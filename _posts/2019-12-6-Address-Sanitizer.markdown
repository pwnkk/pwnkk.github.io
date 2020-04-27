---
layout: post
title:  "fuzz 101"
categories: fuzz
tags: fuzz 
excerpt: fuzz
mathjax: true
---

* content
{:toc}

### Overview
AFL则是fuzzing的一个很好用的工具，全称是American Fuzzy Lop，由Google安全工程师Michał Zalewski开发的一款开源fuzzing测试工具，可以高效地对二进制程序进行fuzzing，挖掘可能存在的内存安全漏洞，如栈溢出、堆溢出、UAF、double free等。由于需要在相关代码处插桩，因此AFL主要用于对开源软件进行测试。配合QEMU等工具，也可对闭源二进制代码进行fuzzing，但执行效率会受到影响

工作原理：

通过对源码进行重新编译时进行插桩（简称编译时插桩）的方式自动产生测试用例来探索二进制程序内部新的执行路径。AFL也支持直接对没有源码的二进制程序进行测试，但需要QEMU的支持。

### 0x00 AFL

下载源码 `https://lcamtuf.coredump.cx/afl/`

直接 `make && make install `

afl-fuzz 命令行参数
```
afl-fuzz 2.52b by <lcamtuf@google.com>

afl-fuzz [ options ] -- /path/to/fuzzed_app [ ... ]

Required parameters:

  -i dir        - input directory with test cases
  -o dir        - output directory for fuzzer findings

Execution control settings:

  -f file       - location read by the fuzzed program (stdin)
  -t msec       - timeout for each run (auto-scaled, 50-1000 ms)
  -m megs       - memory limit for child process (50 MB)
  -Q            - use binary-only instrumentation (QEMU mode)

Fuzzing behavior settings:

  -d            - quick & dirty mode (skips deterministic steps)
  -n            - fuzz without instrumentation (dumb mode)
  -x dir        - optional fuzzer dictionary (see README)

Other stuff:

  -T text       - text banner to show on the screen
  -M / -S id    - distributed mode (see parallel_fuzzing.txt)
  -C            - crash exploration mode (the peruvian rabbit thing)

For additional tips, please consult /usr/local/share/doc/afl/README.

```
创建测试文件 afl_test.c
```
#include <stdio.h> 
#include <stdlib.h> 
#include <unistd.h> 
#include <string.h> 
#include <signal.h> 

int vuln(char *str)
{
    int len = strlen(str);
    if(str[0] == 'A' && len == 66)
    {
        raise(SIGSEGV);
        //如果输入的字符串的首字符为A并且长度为66，则异常退出
    }
    else if(str[0] == 'F' && len == 6)
    {
        raise(SIGSEGV);
        //如果输入的字符串的首字符为F并且长度为6，则异常退出
    }
    else
    {
        printf("it is good!\n");
    }
    return 0;
}

int main(int argc, char *argv[])
{
    char buf[100]={0};
    gets(buf);//存在栈溢出漏洞
    printf(buf);//存在格式化字符串漏洞
    vuln(buf);

    return 0;
}

```
编译命令 `afl-gcc -g -o afl_test afl_test.c`  

在fuzz之前要建立两个文件夹，fuzz_in 用于输入testcase ,fuzz_out 用于记录结果。在fuzz_in 中创建testcase文件 内容随意。

`afl-fuzz -i fuzz_in -o fuzz_out ./afl_test`

![](res/2020-03-23-14-00-17.png)


```
$ cat fuzz_out/crashes/id\:000001\,sig\:11\,src\:000001\,op\:havoc\,rep\:128 | ./afl_test
▒▒▒▒`_it is good!
段错误
```
#### fuzz 界面

* process timing : last new path 是最近发现新路径的时间
* overall results : 这里包括运行的总周期数、总路径数、崩溃次数、超时次数。其中，总周期数可以用来作为何时停止fuzzing的参考。随着不断地fuzzing，周期数会不断增大，其颜色也会由洋红色，逐步变为黄色、蓝色、绿色。一般来说，当其变为绿色时，代表可执行的内容已经很少了，继续fuzzing下去也不会有什么新的发现了。此时，我们便可以通过Ctrl-C，中止当前的fuzzing 
* stage progress :  包括正在测试的fuzzing策略、进度、目标的执行总次数、目标的执行速度

### 0x01 使用AFL fuzz 服务类程序(httpd)

AFL的基本使用只能用文件和stdin，此时就只能patch httpd 让它从文件中接收输入。
在Apache 内部开启一个新线程,连接webserver 将fuzz输入发送过去,新增了`-F`参数指定fuzz的输入文件

```
+static void LAUNCHTHR(char *buf)
+{
+    pthread_t t;
+    pthread_attr_t attr;
+
+    pthread_attr_init(&attr);
+    pthread_attr_setstacksize(&attr, 1024 * 1024 * 8);
+    pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
+
+    pthread_create(&t, &attr, SENDFILE, buf);
+}
```

#### aflnet fuzz 服务端程序

https://github.com/aflnet/aflnet.git

AFLNET 使用mutation 和 state-feedback 指导fuzz 进程。
seed : 用客户端和服务端的交互记录做seed

server 漏洞挖掘的难点
1. server 是有状态的且是消息驱动,接收请求处理后再返回信息。协议的实现通常和定义还有区别
2. server 的返回值取决于当前请求和server 的状态, 这也是AFL所欠缺的地方，没有维护server 内部状态，更适用于文件解析类的程序。



与传统AFL 对比
1. 适合
||AFL|AFLnet|
|--|--|--|
|适用程序|无状态(文件解析)||

### 0x02 libfuzzer 


### 0x01 Address Sanitizer

Address Sanitizer 可以检测出程序的漏洞，通常配合fuzz 一起帮助漏洞挖掘。检测内存越界问题, 包括 heap/stack/全局对象等。

在使用 GCC 或 Clang 编译链接程序时加上 -fsanitize=address 开关,获得更友好的栈追踪信息可以加上 -fno-omit-frame-pointer

简单编写一个UAF 程序

```
#include <stdlib.h>
int main(){
    void *p=malloc(0x100);
    free(p);
    read(0,p,20);
}
//gcc -fsanitize=address -fno-omit-frame-pointer -o demo demo.c
```

不用 -fno-omit-frame-pointer 也能输出栈信息

```
root@ubuntu:/mnt/hgfs/share/Fuzz101/AddressSanitizer# ./demo
AAAAAAA
=================================================================
==91642==ERROR: AddressSanitizer: heap-use-after-free on address 0x611000009f00 at pc 0x7efd6e1abe55 bp 0x7ffeef054740 sp 0x7ffeef053ee8
WRITE of size 8 at 0x611000009f00 thread T0
    #0 0x7efd6e1abe54  (/usr/lib/x86_64-linux-gnu/libasan.so.2+0x45e54)
    #1 0x4007b2 in main (/mnt/hgfs/share/Fuzz101/AddressSanitizer/demo+0x4007b2)
    #2 0x7efd6ddbc82f in __libc_start_main (/lib/x86_64-linux-gnu/libc.so.6+0x2082f)
    #3 0x4006a8 in _start (/mnt/hgfs/share/Fuzz101/AddressSanitizer/demo+0x4006a8)

0x611000009f00 is located 0 bytes inside of 256-byte region [0x611000009f00,0x61100000a000)
freed by thread T0 here:
==91642==AddressSanitizer CHECK failed: ../../../../src/libsanitizer/asan/asan_allocator2.cc:186 "((res.trace)) != (0)" (0x0, 0x0)
    #0 0x7efd6e206631  (/usr/lib/x86_64-linux-gnu/libasan.so.2+0xa0631)
    #1 0x7efd6e20b5e3 in __sanitizer::CheckFailed(char const*, int, char const*, unsigned long long, unsigned long long) (/usr/lib/x86_64-linux-gnu/libasan.so.2+0xa55e3)
    #2 0x7efd6e18376c  (/usr/lib/x86_64-linux-gnu/libasan.so.2+0x1d76c)
    #3 0x7efd6e18463e  (/usr/lib/x86_64-linux-gnu/libasan.so.2+0x1e63e)
    #4 0x7efd6e203400  (/usr/lib/x86_64-linux-gnu/libasan.so.2+0x9d400)
    #5 0x7efd6e205624 in __asan_report_error (/usr/lib/x86_64-linux-gnu/libasan.so.2+0x9f624)
    #6 0x7efd6e1abe72  (/usr/lib/x86_64-linux-gnu/libasan.so.2+0x45e72)
    #7 0x4007b2 in main (/mnt/hgfs/share/Fuzz101/AddressSanitizer/demo+0x4007b2)
    #8 0x7efd6ddbc82f in __libc_start_main (/lib/x86_64-linux-gnu/libc.so.6+0x2082f)
    #9 0x4006a8 in _start (/mnt/hgfs/share/Fuzz101/AddressSanitizer/demo+0x4006a8)
```

### 参考

1. [afl主页](https://lcamtuf.coredump.cx/afl/)
2. [fuzz-apache-with-afl](https://animal0day.blogspot.com/2017/05/fuzzing-apache-httpd-server-with.html)
3. [libFuzzerTutorial](https://github.com/google/fuzzing/blob/master/tutorial/libFuzzerTutorial.md)