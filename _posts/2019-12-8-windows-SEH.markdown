---
layout: post
title:  "windows 异常处理"
categories: REVERSE
tags: REVERSE
excerpt: windows 异常处理
mathjax: true
---

* content
{:toc}

### Overview

借着出来讲课的机会补充一下win逆向方面的短板,先学习一下windows 的异常处理。

### 基本概念
主要使用的两种技术是SEH(结构化异常处理)，VEH(向量化异常处理)。异常分硬件异常(由CPU引发)和软件异常(操作系统和程序引发)

SEH是一种错误保护和修复机制，告诉系统如果出现异常将怎样处理。

### SEH结构

TIB(Thread Information Block 线程信息块) 

SEH以链的形式存在。第一个异常处理中未处理相关异常，它就会被传递到下一个异常处理器，直到得到处理。SEH是由_EXCEPTION_REGISTRATION_RECORD结构体组成的链表

```
ntdll!_EXCEPTION_REGISTRATION_RECORD
   +0x000 Next             : Ptr32 _EXCEPTION_REGISTRATION_RECORD
   +0x004 Handler          : Ptr32 _EXCEPTION_DISPOSITION 
}
```
Next成员指向下一个_EXCEPTION_REGISTRATION_RECORD结构体指针，handler成员是异常处理函数（异常处理器）。若Next成员的值为FFFFFFFF，则表示它是链表最后一个结点



### 参考


