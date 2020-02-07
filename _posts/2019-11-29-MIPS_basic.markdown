---
layout: post
title:  "MIPS"
categories: pwn
tags: pwn 
excerpt: MIPS 
mathjax: true
---

* content
{:toc}

### Overview
本文记录了MIPS的基础知识，以及栈溢出，漏洞利用等内容。MIPS属于RISC精简指令集，所以指令长度固定。

### 寄存器

|寄存器|功能|
| ---- | ---- |
|$v0 ~ $v1|保存表达式或函数返回结果|
|$a0 ~ $a3|函数前4个参数|
| $ra | 返回地址 |
|$fp|保存栈指针|
|$sp|栈顶指针|
|$gp|全局指针 存取静态变量|

### 指令

指令格式，所有指令长度相同都是32位。MIPS架构中最高6位是opcode，剩下24位分为3种类型

* R型指令，连续3个5位二进制码表示三个寄存器的地址，用1个5位二进制码表示移位的位数(不移位就是0)，最后6位
| Opcode(6 bit) | Rs(5) | Rt(5) | Rd(5) | 移位位数(5 bit) | Function码(6 bit) |
* I型指令
| 寄存器地址(5 bit) * 2 | 立即数(16 bit) |
* J型指令
| 跳转目标的指令地址(26 bit)|

1. load/store 指令

* l 开头的加载指令，从存储器中读取数据
* s开头的存储指令，将数据保存到存储器中

LA (将地址保存到寄存器中) : la $t0,label_1  将label_1 地址保存到寄存器中
Li (将立即数保存到寄存器中) : li $t1 ,40    将40 保存到寄存器$t1中
LW (从指定地址加载一个dword型到寄存器中) : lw $s0,0($sp)  等于 $s0 = [$sp+0]

SW (将寄存器存入指定地址) : sw $a0,0($sp) 等于 [$sp+0] = $s0  存入word 大小
MOVE(寄存器之间的传递) ： move $t1,$t2;  $t1=$t2

2. 算数指令

add $t0,$t1,$t2 : $t0 = $t1 + $t2  带符号相加
sub $t0,$t1,$t2 : $t0 = $t1 - $t2  带符号相减

2. 比较指令
slt (Set on Less Than)系列指令和分支跳转结合使用。

slt $Rd,$Rs,$Rt : 在Rs小于$Rt时(有符号比较) 设置寄存器$Rd 为1,否则设置$Rd 为0 
slti $Rt,$Rs,imm : 在Rs小于imm时(有符号比较) 设置寄存器$Rt 为1,否则设置$Rt 为0 

相关的有sltu (unsigned 无符号比较)

3. 分支跳转指令

通过比较两个寄存器的值来决定是否跳转
b target : 直接跳转
beq $t0,$t1,target : 如果 " $t0==$t1 " 则跳转到target 
blt ( < )
ble ( <= )
bgt ( > )
bge ( >= )
bne ( != )

4. 跳转指令
j target  ：无条件跳转
jr $t3    ：跳转到$t3 处
jal target  ：跳转到target , 保存返回地址到$ra 

子函数调用 jal sub_routine_label : 先保存返回地址到$ra  再跳转到子函数
子函数返回 jr $ra : 直接跳到之前保存的返回地址处

