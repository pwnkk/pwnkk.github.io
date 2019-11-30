---
layout: post
title:  "largebin attack"
categories: pwn
tags: pwn 
excerpt: largebin attack
mathjax: true
---

* content
{:toc}

### Overview

largebin attack的关键是最后两个解链操作，如果可以控制fwd的bk_nextsize指针和bk指针，可以实现向任意地址写入victim的地址

### 参考

[从两道题剖析Largebin Attack](https://www.freebuf.com/articles/system/209096.html)

