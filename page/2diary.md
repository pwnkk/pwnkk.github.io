---
layout: page
title: Collections
permalink: /collection/
icon: bookmark
type: page
---

* content
{:toc}

### Diary 2019
记一下日记

#### 2019-10-25

1. 内核利用mmap相关:mwri-mmap-exploitation-whitepaper
* file_operations 中的函数指针定义了操作
* mmap handler 为空的时候依然可以将地址mmap回来，但是没有物理地址与其对应，再访问返回的地址会造成panic
* vm_operations_struct 中定义了处理allocated memory region 的操作

漏洞点： 
* 缺少输入校验
* 整数溢出 / 带符号整数问题
exp: scan cred / cred spray 

没有找到可以练习的漏洞,Framaroot是mmap相关的问题,可惜版本太老, 有空自己写源码复现

2. [Android 扫描漏洞套件](https://github.com/AndroidVTS/android-vts/releases)
扫了nexus5 发现很多media的洞, 有空提上日程
3. [google ctf wp](https://hackmd.io/@gzUPn_btRq2TbqRUdfX9Cw/rkfEQo4gH#Monochromatic)
4. [*ctf hackme](https://github.com/sixstars/starctf2019/tree/master/pwn-hackme)
5. https://duasynt.com/blog/linux-kernel-heap-spray
## Comments

{% include comments.html %}
