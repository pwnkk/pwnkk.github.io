---
layout: post
title:  "PowerPC 逆向基础"
categories: reverse
tags: reverse PowerPC
excerpt: PowerPC 逆向基础
mathjax: true
---


### Overview

简单学习一下Powerpc的逆向基础。
大部分CPU指令集都可分为：数据读写、数值计算、流程控制和设备管理四个部分。软件逆向主要针对前三个部分。PPC（后文中PowerPC都简写为PPC）使用RISC精简指令集，指令字长都是32bit，所以指令一定是4字节对齐的。
### 寄存器

| 寄存器 | 功能 |
| ------ | ------ |
|GPR0-GPR31（共32个寄存器）| 整数运算和寻址通用寄存器.在ABI规范中，GPR1用于堆栈指针，GPR3-GPR4用于函数返回值，GPR3-GPR10用于参数传递 |
| FPR0---FPR31（共32个寄存器）| 用于浮点运算。PPC32和PPC64的浮点数都是64位 |
| LR | 连接寄存器，记录跳转地址，常用于记录子程序返回的地址 |
| CR | 条件寄存器 |
|XER|特殊寄存器，记录溢出和进位标志，作为CR的补充|
|CTR|计数器，用途相当于ECX|
|FPSCR|浮点状态寄存器，用于浮点运算类型的异常记录等，可设置浮点异常捕获掩码|


专用寄存器：有永久功能的寄存器，如堆栈指针（r1）和 TOC 指针（r2）
易失性寄存器: r3-r12 自由修改不需要恢复
非易失性寄存器：修改后需要恢复，事先保存到栈帧中


|通用寄存器|用途|
| ------ | ------ |
|r0 | 用于函数开始 function prologs|
|r1|堆栈指针，类似esp|
|r2|TOC内容表指针，系统调用时，它包含系统调用号|
|r3|第一个参数和返回值|
|r4-r10|函数或系统调用开始的参数，部分情况下r4寄存器也会作为返回值使用|
|r11|用在指针的调用和当作一些语言的环境指针| 
|r12|　 它用在异常处理和glink（动态连接器）代码 |
|r13|　 保留作为系统线程ID |
|r14-r31| 作为本地变量，非易失性| 

|专用寄存器|用途|
| ------ | ------ |
|lr|　链接寄存器，它用来存放函数调用结束处的返回地址|
|ctr|计数寄存器，它用来当作循环计数器，会随特定转移操作而递减|  
|xer|定点异常寄存器，存放整数运算操作的进位以及溢出信息|  
|msr|机器状态寄存器，用来配置微处理器的设定|
|cr |条件寄存器，它分成8个4位字段，cr0-cr7，它反映了某个算法操作的结果并且提供条件分支的机制|  


整数异常寄存器XER是一个特殊功能寄存器，它包括一些对增加计算精度有用的信息和出错信息。XER的格式如下：

|寄存器	|说明|
| ------ | ------ |
|SO 总体溢出标志 | 一旦有溢出位OV置位，SO就会置位|
|OV 溢出标志     | 当发生溢出时置位，否则清零；在作乘法或除法运算时，如果结果超过寄存器的表达范围，则溢出置位|
|CA 进位标志    |当最高位产生进位时，置位，否则清零；扩展精度指令可以用CA作为操作符参与运算|

### 常用指令

1. `li REG, VALUE`加载寄存器 REG，数字为 VALUE
2. `add REGA, REGB, REGC`将 REGB 与 REGC 相加，并将结果存储在 REGA 中
3. `addi REGA, REGB, VALUE`将数字 VALUE 与 REGB 相加，并将结果存储在 REGA 中
4. `mr REGA, REGB`将 REGB 中的值复制到 REGA 中
5. `or REGA, REGB, REGC`对 REGB 和 REGC 执行逻辑 “或” 运算，并将结果存储在 REGA 中
6. `ori REGA, REGB, VALUE`对 REGB 和 VALUE 执行逻辑 “或” 运算，并将结果存储在 REGA 中

`and, andi, xor, xori, nand, nand, and nor`
其他所有此类逻辑运算都遵循与 “or” 或 “ori” 相同的模式

7. `ld REGA, 0(REGB)`使用 REGB 的内容作为要载入 REGA 的值的内存地址
`lbz, lhz, and lwz`它们均采用相同的格式，但分别操作字节、半字和字(“z” 表示它们还会清除该寄存器中的其他内容)

8. `b ADDRESS`跳转(或转移)到地址 ADDRESS 处的指令
9. `bl ADDRESS`对地址 ADDRESS 的子例程调用
10. `cmpd REGA, REGB`比较 REGA 和 REGB 的内容，并恰当地设置状态寄存器的各个位
11. `beq ADDRESS`若之前比较过的寄存器内容等同，则跳转到 ADDRESS

bne, blt, bgt, ble, and bge
它们均采用相同的形式，但分别检查不等、小于、大于、小于等于和大于等于

12. `std REGA, 0(REGB)`使用 REGB 的地址作为保存 REGA 的值的内存地址
`stb, sth, and stw`
它们均采用相同的格式，但分别操作字节、半字和字
13. `sc`对内核进行系统调用


### 调用约定

r1是栈顶指针，r3/r4 是函数返回值
使用stwu，lwzu来代替Push和Pop指令


### 环境搭建

apt-get install libc6-powerpc-cross
apt-get install gcc-powerpc-linux-gnu

### 参考
[PowerPC PWN](https://xz.aliyun.com/t/4975)

qemu-aarch64 -L /usr/aarch64-linux-gnu ./baby_arm
1
调试
可以使用 qemu 的 -g 指定端口

qemu-aarch64 -g 1235 -L /usr/aarch64-linux-gnu ./baby_arm

https://blog.csdn.net/u012655643/article/details/84584974
