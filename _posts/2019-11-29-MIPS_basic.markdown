---
layout: post
title:  "MIPS"
categories: pwn
tags: pwn 
excerpt: MIPS 
mathjax: true
---

* content
{:toc}

### Overview
本文记录了MIPS的基础知识，以及栈溢出，漏洞利用等内容。MIPS属于RISC精简指令集，所以指令长度固定。

### 寄存器

|寄存器|功能|
| ---- | ---- |
|$v0 ~ $v1|保存表达式或函数返回结果|
|$a0 ~ $a3|函数前4个参数|
| $ra | 返回地址 |
|$fp|保存栈指针|
|$sp|栈顶指针|
|$gp|全局指针|

### 