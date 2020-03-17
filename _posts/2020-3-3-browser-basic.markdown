---
layout: post
title:  "browser 基础概念"
categories: pwn
tags: pwn
excerpt: browser 基础概念
mathjax: true
---

* content
{:toc}

### Overview

Javascript 的引擎大体分为四种,Spidermonkey (用于firefox) , JavascriptCore(用于webkit和safari),v8(用于Chrome浏览器),Chakra(用于IE edge浏览器)
每个浏览器引擎包含
1. Parser 和bytecode compiler
2. Interpreter 解释器
3. JIT compiler 
4. runtime 环境
5. garbage collector 垃圾收集

### 1. Parser 和bytecode compiler

用于将javascript 转化为byte code。Parser 标记输入流，解析出AST语法树，随后AST被编译成bytecode。

不同引擎的bytecode格式有所区别，例如Spidermonkey 使用栈虚拟机，而v8采用寄存器虚拟机。因为javascript 是动态类型的语言，需要在运行时根据不同类型采用对应的处理方式。
另外bytecode 通常没有优化过，一方面是为了加快启动时间，另一方面这时还缺少优化需要的类型信息。

### 2.

