---
layout: page
title: Diary
permalink: /diary/
icon: bookmark
type: page
---

* content
{:toc}

### Diary 2019

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

#### 2019-10-31

1. 朋友发来了练手的题目,看了下seccomp过滤,顺便改了下出了道新题目，考一些shellcode 编写和简单leak

[hitcon-quals-2017-seccomp](https://blukat29.github.io/2017/11/hitcon-quals-2017-seccomp/)
[seccomp学习笔记](https://veritas501.space/2018/05/05/seccomp学习笔记/)
2. 整理了下自己的pwn模板, 稍微改了下兼容性

#### 2019-11-1
1. 使用stdout 结构体泄露libc地址，就是修改write_base 的最低位，flag = 0xfbad1800 就行了。
网上题目大都是tcache相关的，我跟着思路出了个旧版libc的，unsorted bin attack 和 fastbin attack 结合起来就行了
2. 相关题目
[lctf2018-pwn-easy_heap](https://ctf-wiki.github.io/ctf-wiki/pwn/linux/glibc-heap/tcache_attack-zh/#challenge-1-lctf2018-pwn-easy_heap)
[sctf2019-pwn_one_heap](http://blog.eonew.cn/archives/1076#pwn_one_heap)

## Comments

{% include comments.html %}
