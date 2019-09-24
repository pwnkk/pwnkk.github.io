---
layout: post
title:  "xinted kafel"
date:   2019-09-10 18:54:00
categories: pwn
tags: pwn
excerpt: xinted kafel试用
mathjax: true
---

### 0x00 概述
试用大佬的xinted-kafel,办awd比赛的时候防止pwn选手上通防，尝试过滤系统调用ptrace 和secommp等
https://github.com/Asuri-Team/xinetd-kafel

### 0x01 试用 

```
apt-get install -y wget bison flex build-essential
```

下载kafel 
git clone https://github.com/google/kafel.git
make

git clone https://github.com/Asuri-Team/xinetd-kafel.git
./configure --prefix=/usr --with-kafel=/opt/kafel --with-loadavg --with-libwrap && make 
执行make




### 参考链接

