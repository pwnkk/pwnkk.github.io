---
layout: post
title:  "逆向工具用法及快捷键"
categories: REVERSE
tags: REVERSE
excerpt: 逆向工具用法及快捷键
mathjax: true
---

* content
{:toc}

### 0x00 IDA

#### IDA-快捷键
|快捷键|功能|
|---|---|
|F5|将反汇编指令还原成伪代码|
|tab| 伪代码和汇编之间切换|
|n  |重命名函数和变量
|shift +e |选中区域提取数据
|edit -> patch program -> change byte  |为程序打补丁
|Shift+F12 | 显示程序中的字符串
|g| 跳转到指定地址
|alt + t |搜索指定字符串
|alt + k |修改堆栈平衡
|/ |伪码注释
|; |汇编码注释  
|alt+L | 选中开始

#### 数据切换

|||
|---|---|
|u | 选中内存区域设置为undefined
|c | 选中区域设置为code 
|d |  切换数据的显示形式 db dw dd 


### 0x01 gdb




