---
layout: post
title:  "Vxworks 逆向"
categories: reverse
tags: reverse Vxworks
excerpt: Vxworks 逆向
mathjax: true
---

* content
{:toc}

### Overview

学习一下固件逆向分析
[题目链接]()

### 固件逆向

`binwalk`查看是zlib压缩的数据
`binwalk -e ` 一把梭,再查看如下

```
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
2054252       0x1F586C        EST flat binary
2088936       0x1FDFE8        HTML document header
2108532       0x202C74        HTML document footer
2110048       0x203260        HTML document header
2115564       0x2047EC        HTML document footer
2119528       0x205768        XML document, version: "1.0"
2119796       0x205874        XML document, version: "1.0"
2119912       0x2058E8        XML document, version: "1.0"
2192512       0x217480        Base64 standard index table
2192580       0x2174C4        Base64 standard index table
2211604       0x21BF14        VxWorks WIND kernel version "2.5"
2225264       0x21F470        Copyright string: "Copyright Wind River Systems, Inc., 1984-2000"
2321952       0x236E20        Copyright string: "copyright_wind_river"
3118988       0x2F978C        Copyright string: "Copyright, Real-Time Innovations, Inc., 1991.  All rights reserved."
3126628       0x2FB564        Copyright string: "Copyright 1984-1996 Wind River Systems, Inc."
3153524       0x301E74        VxWorks symbol table, big endian, first entry: [type: function, code address: 0x1FF058, symbol address: 0x27655C]
```
基本信息: VxWorks, big endian,code address: 0x1FF058, symbol address: 0x27655C

但是并没有显示出PowerPC的架构,反而识别出了ARM
```
root@ubuntu:/mnt/hgfs/share/CTFs/ICS_vxworks/vxwork# binwalk -Y 385

DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
2456          0x998           ARM executable code, 16-bit (Thumb), big endian, at least 2428 valid instructions
```

换一种方式`binwalk -A`扫描指令系统，可以看到PowerPC big endian , 基本上可以确定

```
root@ubuntu:/mnt/hgfs/share/CTFs/ICS_vxworks/vxwork# binwalk -A 385
2046180       0x1F38E4        PowerPC big endian instructions, function epilogue
3150948       0x301464        PowerPC big endian instructions, function epilogue
```

binwalk 版本`Binwalk v2.2.0-5f58fad`

### 计算固件加载地址

1. 找一个字符串的固件地址和加载地址，二者相减就是固件加载地址。
winhex 查找的是最后一个字符串APP_STATION_MODBUS,固件地址是0x26656c
再查看符号表地址0x301E74 处(winhex alt+G) 

```
Offset      0  1  2  3  4  5  6  7   8  9  A  B  C  D  E  F

00301E60   00 00 00 00 00 27 65 6C  00 30 4F 9C 00 00 07 00        'el 0O?   
00301E70   00 00 00 00 00 27 65 5C  00 1F F0 58 00 00 05 00        'e\  餢    
00301E80   00 00 00 00 00 27 65 48  00 1F F5 78 00 00 05 00        'eH  鮴    
```
地址逐渐减小,字符串是倒序存放的, 因此APP_STATION_MODBUS 对应的加载地址就是0x27656c

base = 0x27656c - 0x26656c = 0x100000

2. 查看代码中有没有固定地址加偏移的引用，偏移就可能是固件加载地址。这种方法范围太广没有找到
IDA 打开设置PowerPC big endian , 选了32bit ,打开后全部只是数据,选择开头按c强制反汇编才行。没有得到什么有意义的信息。

3. 从固件头部查找Userinit函数

### 恢复函数表

符号表以16个字节为一组数据，前4个字节是字符串的内存地址，后4个字节是函数的内存位置，然后以另4个特征字节数据与4个字节0x00结尾
起始地址是0x301E64 ,再查看结束地址0x3293A4 是最后一条数据

```
Offset      0  1  2  3  4  5  6  7   8  9  A  B  C  D  E  F

00301E60   00 00 00 00 00 27 65 6C  00 30 4F 9C 00 00 07 00        'el 0O?   
00301E70   00 00 00 00 00 27 65 5C  00 1F F0 58 00 00 05 00        'e\  餢    
00301E80   00 00 00 00 00 27 65 48  00 1F F5 78 00 00 05 00        'eH  鮴    

...

00329390   00 00 00 00 00 23 2A FC  00 33 94 94 00 00 09 00        #*?3敂    
003293A0   00 00 00 00 00 23 2A F4  00 33 9A 64 00 00 09 00        #*?3歞    
003293B0   00 00 27 55 00 03 C1 D8  00 03 EB 40 00 03 FF E4     'U  霖  隌  ?
003293C0   00 05 9B A8 00 06 0C D0  00 06 20 44 00 06 42 44     洦   ?  D  BD

```

使用IDA python (IDA pro 6.8 / win7)

```
from idaapi import *
import time
load = 0x1000
eastart = load + 0x301E64
eaEnd = load + 0x3293A4

ea = eastart
while ea < eaEnd:
    offset = 0
    MakeStr(Dword(ea-offset),BADADDR)
    sName = GetString(Dword(ea-offset),-1,ASCSTR_C)
    print sName
    if sName:
        eaFunc = Dword(ea-offset+4)
        MakeName(eaFunc,sName)
        MakeCode(eaFunc)
        MakeFunction(eaFunc,BADADDR)
    ea=ea+16
```
恢复出了部分函数名，中途报了很多的错误。但是并没有发现loginDefaultEncrypt

尝试一下插件[vxhunter](https://github.com/PAGalaxyLab/vxhunter) 支持三种工具,在linux下尝试Ghidra逆向

1. 安装openjdk-11.0.2_linux-x64_bin.tar.gz (在win共享目录下不能解压)

2. 创建项目，import file , cpu选择 `PowerPC	default	32	big	default` , options 配置base address 为0x1000 , 询问是否分析，选择不分析。
3. 我主要使用了vxhunter 中ghidra 目录下 `vxhunter_core.py` 和  `vxhunter_firmware_init.py`,直接在script manager中新建了脚本，把脚本复制进去了。(放到~/ghidra_scripts中并没有生效)

![](IMG/2019-11-25-Vxworks_re/vxhunter.png)
确实能恢复出来
![](IMG/2019-11-25-Vxworks_re/result.png)

题目已知hash值cQwwddSRxS 求key

### 参考
[再解Vxworks加密漏洞](https://www.freebuf.com/vuls/177036.html)

[工控固件逆向](http://www.icsmaster.org/archives/ics/784)

[固件逆向分析](https://paper.seebug.org/613/)

