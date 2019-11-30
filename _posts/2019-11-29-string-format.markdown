---
layout: post
title:  "printf 格式化字符串总结"
categories: pwn
tags: pwn 
excerpt: printf 格式化字符串总结
mathjax: true
---

* content
{:toc}

### Overview

格式化字符串是比较传统的漏洞,漏洞的形成虽然很简单`printf(buf)`,只要buf可控即可，但是漏洞功能很强大，既能任意地址读也能任意地址写。
后续利用一般是覆盖got表
1. 突破次数限制问题
2. 一次写入多个地址
3. 控制exit, 控制栈地址
4. .fini_array  

静态链接：.fini_array 可写, 但是只能用一次
 ► 0x4019c0 <__libc_csu_fini+32>    call   qword ptr [rbx*8 + 0x6caee0] <0x400bb1>

### 参考


