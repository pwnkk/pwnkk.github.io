---
layout: post
title:  "Address Sanitizer 101"
categories: pwn
tags: pwn 
excerpt: Address Sanitizer
mathjax: true
---

* content
{:toc}

### Overview
Address Sanitizer 可以检测出程序的漏洞，通常配合fuzz 一起帮助漏洞挖掘。
检测内存越界问题, 包括 heap/stack/全局对象等。

### Get Your Hands Dirty

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

[from-read-glibc-to-rce-x86_64](https://amriunix.com/post/from-read-glibc-to-rce-x86_64/?from=timeline)

