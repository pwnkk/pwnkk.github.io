---
layout: post
title:  "pwn题目调试问题总结"
categories: pwn
tags: debug
excerpt: 源码调试/跨libc调试/pie地址偏移
mathjax: true
---

* content
{:toc}

### Overview

工欲善其事,必先利其器。
参考大牛的脚本对自己的exp模板做了一些修改，做pwn的时候脚本的自动化程度越高越能将精力放在漏洞利用上面。
解决的三个问题
1. 跨libc调试
2. libc源码调试
3. PIE地址偏移
后续再总结漏洞利用方面的模板

#### 1.跨libc调试

现在很多PWN题目的libc都考察新版本libc中的tcache 相关利用, 附带着libc2.27 / 2.29 的文件, 但是ubuntu16.04的默认是libc2.23,这篇就是解决如何在这种情况下实现高版本libc的执行调试。

以mergerheap 题目为例,给出的是libc-2.27.so , 本机环境ubuntu 16.04 

通常情况下使用pwntools 设置环境变量 加载特定libc 如下
exp.py

```python
from pwn import *
p = process("./mergeheap",env={"LD_PRELOAD":"./libc-2.27.so"})
p.interactive()
```
但是这样启动失败

把ubuntu18.04 的ld拷贝到当前目录，使用patchelf 修改程序的ld路径
` patchelf --set-interpreter ./ld-linux-x86-64.so.2 ./mergeheap`
再执行exp.py 就能跑起来了

#### 2. 源码调试/PIE

* 为什么要源码调试
libc源码调试能够加深对于libc中heap分配,IO处理等流程的理解,也更利于快速定位问题
例如错误提示"corrupted double-linked list"​，从源码中定位到

```
    if (__builtin_expect (FD->bk != P || BK->fd != P, 0))		      \
      malloc_printerr (check_action, "corrupted double-linked list", P, AV);  \
```

就知道是unlink操作 fd和bk的校验没有通过，再检查内存中对应的值即可

参考其他大佬的exp

```python
from pwn import *

context.terminal = ["tmux","splitw","-h"]
def dbg(breakpoint):
    glibc_dir = '/opt/glibc-2.23/'
    gdbscript = 'directory %smalloc\n' % glibc_dir
    gdbscript += 'directory %sstdio-common/\n' % glibc_dir
    gdbscript += 'directory %sstdlib/\n' % glibc_dir
    gdbscript += 'directory %slibio\n' % glibc_dir
    elf_base = int(os.popen('pmap {}| awk \x27{{print \x241}}\x27'.format(io.pid)).readlines()[1], 16)if elf.pie else 0 
    gdbscript += 'b *{:#x}\n'.format(int(breakpoint) + elf_base) if isinstance(breakpoint, int) else breakpoint

    gdb.attach(io, gdbscript)
    time.sleep(1)

elf = ELF("./mergeheap")
io = process("./mergeheap",env={"LD_PRELOAD":"./libc-2.27.so"})
dbg(0xbd5)

io.interactive()
```

1. 使用gdb directory命令指定libc源码的目录,当调试到libc相关函数的时候即可定位到源码
2. 解决PIE的问题,可以断到特定函数地址


还可以编译自带符号的libc.so ,使用时指定给出的libc版本，修改程序对应的ld和libc路径

下载编译libc, 借用ray_cp大佬的脚本
https://github.com/ray-cp/pwn_debug/blob/master/build.sh

完整的exp模板如下

```python
#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from pwn import *
import sys
import os
debug = 1
exe = "./mergeheap"

r = lambda x:io.recv(x)
ru = lambda x:io.recvuntil(x)
rud = lambda x:io.recvuntil(x,drop=True)
rul = lambda x:io.recvline()
sd = lambda x:io.send(x)
sl = lambda x:io.sendline(x)
sea = lambda x,y:io.sendafter(x,y)
sela = lambda x,y:io.sendlineafter(x,y)

context.terminal = ["tmux","splitw","-h"]
elf = ELF(exe)
context.arch = elf.arch

if debug:
    context.log_level = "debug"

arena64 = 0x3c4b20
arena32 = 0x1b2780

def pre(libc_version):
    glibc_dir = '/glibc/{arch}/{libc}/lib/libc-{libc}.so'.format(arch=elf.arch,libc=str(libc_version))
    io = process(exe,env={"LD_PRELOAD":glibc_dir})
    ld_dir = '/glibc/{arch}/{libc}/lib/ld-{libc}.so'.format(arch=elf.arch,libc=str(libc_version))
    cmd = "patchelf --set-interpreter {} {}".format(ld_dir,os.getcwd()+"/"+exe)
    os.system(cmd)
    return io
 
def dbg(breakpoint):
    elf_base = int(os.popen('pmap {}| awk \x27{{print \x241}}\x27'.format(io.pid)).readlines()[1], 16)if elf.pie else 0 
    gdbscript = 'b *{:#x}\n'.format(int(breakpoint) + elf_base) if isinstance(breakpoint, int) else breakpoint
    gdb.attach(io, gdbscript)
    time.sleep(1)

if len(sys.argv)>1:
    io = remote(sys.argv[1],int(sys.argv[2]))
    #libc = ELF("./libc.so.6")
else:
    io = pre(2.27)
    libc = elf.libc


io.interactive()
```


### 参考链接

https://github.com/ray-cp/pwn_debug
