---
layout: post
title:  "house of orange"
date:   2019-09-02 15:14:54
categories: pwn
tags: pwn
excerpt: house of orange
mathjax: true
---

### 0x00 概述
正好用到house of orange 相关的知识，做一个简单的记录。

一句话概括house of orange ：没有free 操作的情况下，通过将top chunk free掉，进而创造出unsorted bin , 利用unsorted bin attack 写入main_arena+88 到__IO_list_all,进而通过伪造FILE 结构体获得shell。

### 0x01 没有free 如何创造unsorted bin 

malloc.c 中 sysmalloc 函数中
```c
sysmalloc (INTERNAL_SIZE_T nb, mstate av){
    ...
  if (av == NULL
      || ((unsigned long) (nb) >= (unsigned long) (mp_.mmap_threshold)
	  && (mp_.n_mmaps < mp_.n_mmaps_max)))
    {
      char *mm;           /* return value from mmap call*/

    try_mmap:
```
当请求size >= mp_.mmap_threshold (128*1024) 时会调用mmap 分配内存

中间有如下check
```c
  old_top = av->top;
  old_size = chunksize (old_top);
  old_end = (char *) (chunk_at_offset (old_top, old_size));

  brk = snd_brk = (char *) (MORECORE_FAILURE);

  /*
     If not the first time through, we require old_size to be
     at least MINSIZE and to have prev_inuse set.
   */

  assert ((old_top == initial_top (av) && old_size == 0) ||
          ((unsigned long) (old_size) >= MINSIZE &&
           prev_inuse (old_top) &&
           ((unsigned long) old_end & (pagesize - 1)) == 0));

  /* Precondition: not enough current space to satisfy nb request */
  assert ((unsigned long) (old_size) < (unsigned long) (nb + MINSIZE));
```

1. old_top 的prev_in_use 位为1
2. old_size > MINSIZE 
3. old_end & (pagesize - 1)) == 0 即 当前 topchunk_addr + size 的后三位要都为0

```c
          if (old_size >= MINSIZE)
            {
              set_head (chunk_at_offset (old_top, old_size), (2 * SIZE_SZ) | PREV_INUSE);
              set_foot (chunk_at_offset (old_top, old_size), (2 * SIZE_SZ));
              set_head (old_top, old_size | PREV_INUSE | NON_MAIN_ARENA);
              _int_free (av, old_top, 1);
            }
```
最后将会把old_top chunk free掉.

###0x02 攻击__IO_list_all

1. 为什么要攻击 __IO_list_all ?
__IO_list_all 是文件流类利用中常见的攻击目标，在堆程序中当malloc 出错时会触发如下流程

```c
malloc_printerr
   _libc_message(error msg)
       abort
           _IO_flush_all_lockp -> JUMP_FILE(_IO_OVERFLOW)
```

_IO_flush_all_lockp流程如下
```c
int 
_IO_flush_all_lockp (int do_lock)
{
  struct _IO_FILE *fp;
... 

  last_stamp = _IO_list_all_stamp;
  fp = (_IO_FILE *) _IO_list_all;  //覆盖_IO_list_all 在其中伪造结构体
  while (fp != NULL)
    {
      run_fp = fp;
      if (do_lock)
	_IO_flockfile (fp);

      if (((fp->_mode <= 0 && fp->_IO_write_ptr > fp->_IO_write_base)
#if defined _LIBC || defined _GLIBCPP_USE_WCHAR_T
	   || (_IO_vtable_offset (fp) == 0
	       && fp->_mode > 0 && (fp->_wide_data->_IO_write_ptr
				    > fp->_wide_data->_IO_write_base))
#endif
	   )
	  && _IO_OVERFLOW (fp, EOF) == EOF)
    ...
	fp = fp->_chain;
    }
```

覆盖_IO_list_all 在其中伪造_IO_FILE结构体，需要满足两个条件
1. fp->_mode <= 0 
2. fp->_IO_write_ptr > fp->_IO_write_base

可以用 `p *((struct _IO_FILE_plus*)addr)` 在调试器中确认

libio.h 中 _IO_FILE结构体定义
```c
struct _IO_FILE {
  int _flags;		/* High-order word is _IO_MAGIC; rest is flags. */
#define _IO_file_flags _flags
  /* Note:  Tk uses the _IO_read_ptr and _IO_read_end fields directly. */
  char* _IO_read_ptr;	/* Current read pointer */
  char* _IO_read_end;	/* End of get area. */
  char* _IO_read_base;	/* Start of putback+get area. */
  char* _IO_write_base;	/* Start of put area. */
  char* _IO_write_ptr;	/* Current put pointer. */
  char* _IO_write_end;	/* End of put area. */
  char* _IO_buf_base;	/* Start of reserve area. */
  char* _IO_buf_end;	/* End of reserve area. */
  /* The following fields are used to support backing up and undo. */
  char *_IO_save_base; /* Pointer to start of non-current get area. */
  char *_IO_backup_base;  /* Pointer to first valid character of backup area */
  char *_IO_save_end; /* Pointer to end of non-current get area. */

  struct _IO_marker *_markers;
  struct _IO_FILE *_chain;
  int _fileno;
#if 0
  int _blksize;
#else
  int _flags2;
#endif
  _IO_off_t _old_offset; /* This used to be _offset but it's too small.  */

#define __HAVE_COLUMN /* temporary */
  /* 1+column number of pbase(); 0 is unknown. */
  unsigned short _cur_column;
  signed char _vtable_offset;
  char _shortbuf[1];
  /*  char* _save_gptr;  char* _save_egptr; */
  _IO_lock_t *_lock;
#ifdef _IO_USE_OLD_IO_FILE
};
```

2. 如何伪造结构体
unsorted bin attack 攻击可以写入任意地址，但不可以控制写入的内容，所以__IO_list_all 赋值为 main_arena+88 
bk = __IO_list_all-0x10 即可。
但是覆盖后如何在main_arena 中伪造结构体?

在函数_IO_flush_all_lockp 中如果不能满足条件就会`fp = fp->_chain ` 更新fp，直到fp=0为止。
查看_chain 字段在IO_FILE中的偏移是0x60, 控制fp->_chain 字段指向一个可控位置，进而伪造可控的IO_FILE 结构体即可。

偏移0x60 的地方正好对应着0x60 的small bin 的位置, 因此IO_FILE结构需要构造在一个0x60 大小的small bin 中
将之前的unsorted bin size 修改为0x60 

### 0x03 题目分析 house of orange

功能分析：
1. 

### 参考链接

