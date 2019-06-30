---
layout: page
title: Collections
permalink: /collection/
icon: bookmark
type: page
---

* content
{:toc}

### PWN tips总结

#### 0x00 栈溢出
+ ret2text: 基础栈溢出，测试偏移,覆盖返回地址
+ ret2shellcode
+ ret2csu
+ ret2libc
  + 配合ROP技术泄露libc地址: 32位ROP在栈上布置参数，64位ROP用ROPgadget 设置寄存器，1-6个参数分别为rdi,rsi,rdx,rcx,r8,r9 
  + 重新构造 system("/bin/sh")
+ ret2syscall : 通过设置寄存器构造系统调用,一般用于静态编译的程序

高级利用
+ stack pivot : 栈迁移，用于空间不够的情况， 伪造ebp为要迁移的位置，返回地址放置 leave_ret 地址， 经过两次leave成功改变esp 
  + 或者利用xchg esp ,eax; 等gadget
+ ret2dl_resolve
+ SROP

#### 0x01 堆利用


## Comments

{% include comments.html %}
