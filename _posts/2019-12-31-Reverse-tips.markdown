---
layout: post
title:  "Reverse tips"
categories: REVERSE
tags: REVERSE
excerpt: 记录逆向中的基础知识
mathjax: true
---

* content
{:toc}

### 加密算法

```
int __fastcall MD5Update(int a1, int a2, unsigned int a3)
{
  unsigned int v4; // [sp+4h] [bp-20h]@1
  int v5; // [sp+8h] [bp-1Ch]@1
  int v6; // [sp+Ch] [bp-18h]@1
  int i; // [sp+14h] [bp-10h]@4
  int v8; // [sp+18h] [bp-Ch]@1

  v6 = a1;
  v5 = a2;
  v4 = a3;
  v8 = (*(_DWORD *)(a1 + 16) >> 3) & 0x3F;
  *(_DWORD *)(a1 + 16) += 8 * a3;
  if ( *(_DWORD *)(a1 + 16) < 8 * a3 )
    ++*(_DWORD *)(a1 + 20);
  *(_DWORD *)(a1 + 20) += a3 >> 29;
  if ( a3 < 64 - v8 )
  {
    i = 0;
  }
  else
  {
    MD5_memcpy(a1 + v8 + 24, a2, 64 - v8);
    MD5Transform(v6, v6 + 24);
    for ( i = 64 - v8; i + 63 < v4; i += 64 )
      MD5Transform(v6, v5 + i);
    v8 = 0;
  }
  return MD5_memcpy(v6 + v8 + 24, v5 + i, v4 - i);
}

//----- (00000C78) --------------------------------------------------------
int __fastcall MD5Final(int a1, int a2)
{
  unsigned int v2; // r3@2
  int v4; // [sp+0h] [bp-1Ch]@1
  int v5; // [sp+4h] [bp-18h]@1
  char v6; // [sp+8h] [bp-14h]@1
  int v7; // [sp+10h] [bp-Ch]@1
  unsigned int v8; // [sp+14h] [bp-8h]@4

  v5 = a1;
  v4 = a2;
  Encode((int)&v6, a2 + 16, 8u);
  v7 = (*(_DWORD *)(v4 + 16) >> 3) & 0x3F;
  if ( (unsigned int)v7 > 0x37 )
    v2 = 120 - v7;
  else
    v2 = 56 - v7;
  v8 = v2;
  MD5Update(v4, (int)_data_start, v2);
  MD5Update(v4, (int)&v6, 8u);
  Encode(v5, v4, 0x10u);
  return MD5_memset(v4, 0, 0x58u);
}

//----- (00000D38) --------------------------------------------------------
int __fastcall vMD5Crypt(int a1, unsigned int a2, int a3)
{
  int v3; // ST0C_4@1
  unsigned int v4; // ST08_4@1
  int v5; // ST04_4@1
  char v7; // [sp+10h] [bp-5Ch]@1

  v3 = a1;
  v4 = a2;
  v5 = a3;
  MD5Init((int)&v7);
  MD5Update((int)&v7, v3, v4);
  return MD5Final(v5, (int)&v7);
}

//----- (00000D8C) --------------------------------------------------------
int __fastcall vMD5CryptStr(int a1, unsigned int a2, int a3)
{
  ...
  v3 = a1;
  v4 = a2;
  v16 = (int)"0123456789ABCDEF";
  i = 0;
  v7 = 0;
  v8 = 0;
  v9 = 0;
  v10 = 0;
  v11 = 0;
  v12 = 0;
  v13 = 0;
  v14 = 0;
  v15 = 0;
  v18 = a3;
  MD5Init((int)&v6);
  MD5Update((int)&v6, v3, v4);
  result = MD5Final((int)&v7, (int)&v6);
  for ( i = 0; i <= 15; ++i )
  {
    *(_BYTE *)v18++ = *(_BYTE *)(v16 + ((signed int)(unsigned __int8)v19[i - 48] >> 4));
    *(_BYTE *)v18++ = *(_BYTE *)(v16 + (v19[i - 48] & 0xF));
  }
  *(_BYTE *)v18 = 0;
  return result;
}
// D8C: using guessed type char var_4[4];

//----- (00000F28) --------------------------------------------------------
int __fastcall MD5Transform(int a1, int a2)
{
  ...
  v2 = a1;
  v84 = *(_DWORD *)a1;
  v85 = *(_DWORD *)(a1 + 4);
  v86 = *(_DWORD *)(a1 + 8);
  v87 = *(_DWORD *)(a1 + 12);
  Decode((int)&v68, a2, 0x40u);
  v3 = __ROR4__((v85 & v86 | ~v85 & v87) + v68 + v84 - 680876936, 25);
  v84 = v3 + v85;
  v4 = __ROR4__(((v3 + v85) & v85 | ~(v3 + v85) & v86) + v69 + v87 - 389564586, 20);
  v87 = v4 + v84;
  v5 = __ROR4__(((v4 + v84) & v84 | ~(v4 + v84) & v85) + v70 + v86 + 606105819, 15);
  v86 = v5 + v87;
  v6 = __ROR4__(((v5 + v87) & v87 | ~(v5 + v87) & v84) + v71 + v85 - 1044525330, 10);
  v85 = v6 + v86;
  ... 很多ROR4
  v65 = __ROR4__(((~v85 | (v64 + v84)) ^ v84) + v70 + v86 + 718787259, 17);
  v86 = v65 + v87;
  v66 = __ROR4__(((~v84 | (v65 + v87)) ^ v87) + v77 + v85 - 343485551, 11);
  v85 = v66 + v86;
  *(_DWORD *)v2 += v84;
  *(_DWORD *)(v2 + 4) += v85;
  *(_DWORD *)(v2 + 8) += v86;
  *(_DWORD *)(v2 + 12) += v87;
  return MD5_memset((int)&v68, 0, 0x40u);
}

//----- (000025E0) --------------------------------------------------------
int __fastcall Encode(int result, int a2, unsigned int a3)
{
  int v3; // [sp+28h] [bp-Ch]@1
  unsigned int i; // [sp+2Ch] [bp-8h]@1
  int *v5; // [sp+34h] [bp+0h]@1

  v5 = (int *)&v5;
  v3 = 0;
  for ( i = 0; i < a3; i += 4 )
  {
    *(_BYTE *)(result + i) = *(_DWORD *)(a2 + 4 * v3);
    *(_BYTE *)(result + i + 1) = *(_WORD *)(a2 + 4 * v3) >> 8;
    *(_BYTE *)(result + i + 2) = *(_DWORD *)(a2 + 4 * v3) >> 16;
    *(_BYTE *)(result + i + 3) = *(_DWORD *)(a2 + 4 * v3++) >> 24;
  }
  return result;
}

//----- (00002708) --------------------------------------------------------
int __fastcall Decode(int result, int a2, unsigned int a3)
{
  int v3; // [sp+24h] [bp-10h]@1
  int v4; // [sp+28h] [bp-Ch]@1
  unsigned int i; // [sp+2Ch] [bp-8h]@1
  int *v6; // [sp+34h] [bp+0h]@1

  v6 = (int *)&v6;
  v3 = result;
  v4 = 0;
  for ( i = 0; i < a3; i += 4 )
  {
    result = a2;
    *(_DWORD *)(v3 + 4 * v4++) = *(_BYTE *)(a2 + i) | (*(_BYTE *)(a2 + i + 1) << 8) | (*(_BYTE *)(a2 + i + 2) << 16) | (*(_BYTE *)(a2 + i + 3) << 24);
  }
  return result;
}

```

### MFC

1. 打开文件 
