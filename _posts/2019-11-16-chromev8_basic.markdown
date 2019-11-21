---
layout: post
title:  "v8入门"
categories: pwn
tags: browser
excerpt: chrome v8 入门
mathjax: true
---

* content
{:toc}

### Overview

这篇主要是做的学习笔记，争取系统的学习一下


创建任意地址读写: ArrayBuffer和TypedArray
经常在JIT中嵌入shell代码

inline函数，浮点数经常使用(xmm寄存器) 仅靠gdb非常困难

v8构造升级
当時: Full-Codegen(JIT生成) + Crankshaft(最適化1) + TurboFan(最適化2) 
現在: Ignition(JIT生成) + TurboFan(最適化)

知识：
1. 编译器和优化知识 : 编译器之间的关系和调用最优化的触发条件
2. GC知识 : 安装和触发条件
3. v8的底层构造表示：整数/double / 指针/字符串/特殊值/ArrayBuffer 等


### v8简介

用C++编写的，用于解释和运行javascript 的引擎
将javascript 解析为AST(抽象语法树)，再转为基础JIT编译组件执行

了解v8结构
1. 编写任意地址读写的代码
2. 稳定的exp

编译器的历史变迁
2008 年: 刚发布 由Full-Codegen 直接生成并执行机器语言的AST,JIT生成速度快但机器码有很多冗余，可以进一步优化
2010年：为了优化hot-code引入了Crankshaft
2015年: 引入了Turbofan 满足javascript的新规格
2017年: 提高维护效率 引入了生成中间语言的Ignition
2018年:Full-Codegen 和Crankshaft 完成任务被删除了

题目所处的2016年当时是Codegen,Crankshaft和Turbofan同时存在的，没有Ignition
hidden class 和 Inline 也在使用

### 编译器和优化
Baseline编译器
1. Full-Codegen

优化机制(重要)
1. hidden class 
2. Inline

优化编译器
1. Crankshaft
2. Turbofan (重要)


### Full-Codegen

把AST转成汇编
JIT编译器：运行时编译，一种提高运行速度的机制
v8把javascript代码转换成机器语言，放到RWX权限的JIT区域中并跳转过来直接执行，没有优化

Full-Codegen生成准最优化代码，生成速度快，但是执行速度慢很多

### 优化机制

1. 利用高速缓存
2. 编译成效率更高的JIT代码

运行时判断优化是否最佳
* 主线程执行机器语言
* Runtime-Profiler 在另一个线程上检测运行状况，根据结果判断是否应该进行优化

优化1:利用类型信息的高速缓存
利用hidden class 信息，缓存inline caching调用的地址和参照偏移

优化2:利用Crankshaft/Turbofan优化编译
* 有排他性：同一段代码只能被一个编译
* 优化编译要在检测出hot-code之后才启动

### Named properties vs. elements

Named properties `{a: "foo", b: "bar"}` 这个对象有两个命名属性"a" 和 "b" . 每个对象都有一个关联的隐藏类，其中存储着对象形状的信息，以及从属性名到属性的映射关系。
element `["foo", "bar"] ` 有整数索引,主要使用pop,slice 操作。

Elements 和 properties 可以是 arrays 或 dictionaries


### hidden class

javascript 中 用函数模拟表达类定义
```
function Point(x,y){
    this.x=x;
    this.y=y;
}
var p = new Point(1,2); // 生成object 
var q = new Point(1,2); // 生成object 

```
为了实现属性访问的高速化

Javascript里是通过字符串匹配来查找属性值的,V8借用了类和偏移位置的思想，将本来通过属性名匹配来访问属性值的方法进行了改进，使用类似C++编译器的偏移位置机制来实现，这就是隐藏类
隐藏类将对象划分成不同的组，对于组内对象拥有相同的属性名和属性值的情况，将这些组的属性名和对应的偏移位置保存在一个隐藏类中，组内所有对象共享该信息。同时，也可以识别属性不同的对象

p和q因为有同样的属性名，所以被归类为同一个组，共享一个隐藏类,在访问属性时只需要提供偏移就行了。但是如果执行了q.z =2 那么p,q 就不认为是同一个组的。

hidden class 的生成过程


每个object 的第一个字段就指向hidden class 
hidden class 其中 bit field 3 (存储属性的数量)和 指向descriptor array的指针。descriptor array中包含named properties信息 例如 name 和存储value的地址


特点：
1. 每个object 都有一个隐藏类
2. 如果object布局发生变化就会创建或找到新的隐藏类，附加到这个object上。
3. VM可以通过简单的比较隐藏类来检查关于对象布局的假设

### 三种 Named properties

In-object vs. normal properties



### inline caching

正常访问对象属性的过程是：首先获取隐藏类的地址，然后根据属性名查找偏移值，然后计算该属性的地址。虽然相比以往在整个执行环境中查找减小了很大的工作量，但依然比较耗时。能不能将之前查询的结果缓存起来，供再次访问呢？当然是可行的，这就是内嵌缓存。
内嵌缓存的大致思路就是将初次查找的隐藏类和偏移值保存起来，当下次查找的时候，先比较当前对象是否是之前的隐藏类，如果是的话，直接使用之前的缓存结果，减少再次查找表的时间。当然，如果一个对象有多个属性，那么缓存失误的概率就会提高，因为某个属性的类型变化之后，对象的隐藏类也会变化，就与之前的缓存不一致，需要重新使用以前的方式查找哈希表。


核心思想：如果我们对一个对象的假设是正确的(通过 hidden class 检查对象布局)，可以创建一个fast path 可以在不进入runtime的情况下快速加载obj的属性，但是假设很难保证正确
所以load/store 观察学习，一旦看到对象就缓存对象布局，就使后续类似对象变得更快。可以应用于任何动态行为的操作，例如算术运行，函数方法的调用，还可以缓存多个fast path 这就是多态(polymorphic)

实现inline cache

1. 修改调用路径，调用stubs(一段生成的原生代码)
2. stubs是基于某种假设创建的代码，如果stubs发现不适应这个object，就patch自己适应新的情况

* 每个IC都有一个全局变量用于模拟修改调用指令
* 使用闭包而不是stubs(存根)

在v8中查找IC site 的patch操作是通过检查栈上的返回地址实现的

每个属性load/store site 都有自己的IC和IC id 


是对以下动作缓存优化的机制
参照，代入(LoadIC, StoreIC) 
 配列アクセス(KeyedLoadIC, KeyedStoreIC) 
 二項演算(BinaryOpIC) ※最近のV8ではなくなった？ 
 関数呼出(CallIC) 
 比較(CompareIC) 
 ブーリアン化(ToBooleanIC) ※最近のV8ではなくなった？



有以下4种状态
* Premonomorphic 只通过一次 没有开始IC
* Monomorphic  一个IC
* Polymorphic  多个IC 快
* Megamorphi   多个IC 慢

调试(--trace-ic)

### Crankshaft 和Turbofan

1. 优化编译器的条件

* 在函数/循环中没有对应的优化算法： eval / debugger 相关
* 使用asm 的用Turbofan
* Crankshaft没有对应的情况，try-catch / with 用Turbofan

Turbofan 优化
•  Loop peeling / Loop elimination
•  Escape analysis
•  Lowering
•  Eﬀect and control linearize
•  Dead code elimination
•  Control ﬂow optimization
•  Memory optimization

逆优化: 优化后的代码不一定都是好用的

Assembler

调试 --trace-opt

### 源码阅读的重要概念

exploit时不那么重要，但是阅读源码时最好知道

* Handle/HandleScope : 为了方便GC追踪，将各个object都用`Handle<T>`型管理
```
Handle : A Handle provides a reference to an object that survives relocation by the garbage collector.
HandleScope : A stack-allocated class that governs a number of local handles.
```
* Context:
* Isolate: v8以Isolate作为隔离的单位，也就是说，一个v8的运行实例对应了一个Isolate，所有运行时的信息都不能采用全局的方式，而是放置在Isolate里，不同的Isolate于是就可以对应不同的运行环境了

Platform 
Interpreter
blob
ICU
third_party
tools

### 垃圾收集

一种在V8中单独管理JavaScript对象（称为HeapObject）的机制
* 检测废弃的对象并自动释放它们
* 使用与Linux heap不同的区域

heap区域
* GC管理JS object ，普通object由C++ 管理
* 虽然是一个JavaScript object，但有些例外，存放在heap而不是HeapObject（例如JSArrayBuffer的BackingStore）

v8将动态内存(堆内存)分成了多个区域，对于垃圾收集器来说，分为了:
new space: 用来放新建立的对象
old pointer space: 用来放”旧的”指针
old data space: 用来放”旧的“数据
large object space: 用来放占用比较大的对象
code space: 用来放jit编译的代码
cell space, property cell space, map space: 对我们来说暂时不重要
这里出现了新旧的概念，对于新对象来说，垃圾收集器会经常性的去尝试看能不能回收，如果一个对象经历过两次回收(这里叫做scavenge)都还没有被回收，于是这个对象就会被放到旧空间当中。
我们经常关注code space用来放jit编译的代码。

### 对象表示

* SMI
v8中没有整数，全是double，用SMI(small integer)来实现
Tagged values : 区分整数和指针
在v8中，smi表示为32位,最低位为标志位，用0表示该数据为smi，高31位为整数数值。对于指针，其末位为1，将1去掉即为指针真实值。
64bit 情况下 `SMI : |signed value(32bit) | 0-padding(32bit)|0 |`

* Heapobject 指针
32bit : `|Pointer(31bit)| 1|`
64bit : `|Pointer(63bit)| 1|`

* Heapnumber 
对象值为double 超出SMI范围
`|Pointer(63bit)| 1| --> | (Map*) | (value) |`

```cpp
V8 version 8.0.0 (candidate) [sample shell]
> var a=[0xdeadbee,0xdeadbeef,"asd"]
d8> %DebugPrint(a)
DebugPrint: 0x14bb8728d499: [JSArray]
 - map: 0x2166aa502729 <Map(PACKED_ELEMENTS)> [FastProperties]
 - prototype: 0x308152b05539 <JSArray[0]>
 - elements: 0x14bb8728d441 <FixedArray[3]> [PACKED_ELEMENTS (COW)]
 - length: 3
 - properties: 0x1bf63f282251 <FixedArray[0]> {
    #length: 0x1bf63f2cff89 <AccessorInfo> (const accessor descriptor)
 }
 - elements: 0x14bb8728d441 <FixedArray[3]> {
           0: 233495534
           1: 0x308152b27151 <Number 3.73593e+09>
           2: 0x308152b27021 <String[3]: asd>

gdb-peda$ x/20gx 0x308152b27151-1
0x308152b27150: 0x00000cd5d4e02571 (kMapoffset *)      0x41ebd5b7dde00000 (kValueOffset)

gdb-peda$ job 0x00000cd5d4e02571
0xcd5d4e02571: [Map]
 - type: HEAP_NUMBER_TYPE
 - instance size: 16
 - elements kind: HOLEY_ELEMENTS
 - unused property fields: 0
 - enum length: invalid
 - stable_map
 - back pointer: 0x1bf63f2822e1 <undefined>
 - prototype_validity cell: 0
 - instance descriptors (own) #0: 0x1bf63f282231 <DescriptorArray[2]>
 - layout descriptor: (nil)
 - prototype: 0x1bf63f282201 <null>
 - constructor: 0x1bf63f282201 <null>
 - dependent code: 0x1bf63f282251 <FixedArray[0]>
 - construction counter: 0
```
* propertyCell
![propertyCell](IMG/v8_basic/PropertyCell.png)

* String
![propertyCell](IMG/v8_basic/string.png)
* oddball
表示特殊值 例如True False等
![oddball](IMG/v8_basic/oddball.png)

### JSobject



### ArrayBuffer && TypedArray

![ArrayBuffer && TypedArray](IMG/v8_basic/AT.png)
* ArrayBuffer
一个可以直接从JavaScript访问内存的特殊数组
其中的BackingStore 内存区域可以用TypedArray来读写

* TypedArray
用来生成内存的视图，通过9个构造函数，可以生成9种数据格式的视图，
比如 Uint8Array/Int16Array/Float64Array

![ArrayBuffer && TypedArray](IMG/v8_basic/AT2.png)

* 常见利用
    1. 可以如果修改ArrayBuffer中的Length，那么就能够造成越界访问。
    2. 如果能够修改BackingStore指针，那么就可以获得任意读写的能力了，这是非常常用的一个手段
    3. 可以通过BackingStore指针泄露堆地址，还可以在堆中布置shellcode。

* 实践

```js
var ab = new ArrayBuffer(0x100);
var t64 = new Float64Array(ab);
t64[0] = 6.953328187651540e-310;//字节序列是0x00007fffdeadbeef
var t32 = new Uint32Array(ab);
k = [t32[1],t32[0]]

%DebugPrint(ab);

d8> %DebugPrint(ab);
DebugPrint: 0x1ee2038d469: [JSArrayBuffer]
 - map: 0x1e967de03fe9 <Map(HOLEY_ELEMENTS)> [FastProperties]
 - prototype: 0x2fb216192981 <Object map = 0x1e967de04041>
 - elements: 0x191412a02251 <FixedArray[0]> [HOLEY_ELEMENTS]
 - embedder fields: 2
 - backing_store: 0x560efcd94bd0
 - byte_length: 256
 - neuterable
 - properties: 0x191412a02251 <FixedArray[0]> {}
 - embedder fields = {
    (nil)
    (nil)
 }

```

### JS function
![js function](IMG/v8_basic/js-function.png)

实际调试的结果和图片里的不太一样
```
d8> function f(){}
undefined
d8> %DebugPrint(f)
DebugPrint: 0x35fd1e6a7309: [Function] in OldSpace
 - map: 0xc480e602519 <Map(HOLEY_ELEMENTS)> [FastProperties]
 - prototype: 0x35fd1e684611 <JSFunction (sfi = 0x247fc3105559)>
 - elements: 0x247fc3102251 <FixedArray[0]> [HOLEY_ELEMENTS]
 - function prototype:
 - initial_map:
 - shared_info: 0x35fd1e6a7129 <SharedFunctionInfo f>
 - name: 0x247fc3105bd9 <String[1]: f>
 - builtin: CompileLazy
 - formal_parameter_count: 0
 - kind: NormalFunction
 - context: 0x35fd1e683eb1 <FixedArray[234]>
 - code: 0x337e72c1fe41 <Code BUILTIN>
 - source code: (){}
 - properties: 0x247fc3102251 <FixedArray[0]> {
    #length: 0x247fc3150299 <AccessorInfo> (const accessor descriptor)
    #name: 0x247fc3150229 <AccessorInfo> (const accessor descriptor)
    #arguments: 0x247fc3150149 <AccessorInfo> (const accessor descriptor)
    #caller: 0x247fc31501b9 <AccessorInfo> (const accessor descriptor)
    #prototype: 0x247fc3150309 <AccessorInfo> (const accessor descriptor)
 }

gdb-peda$ x/10gx 0x35fd1e6a7309-1
0x35fd1e6a7308: 0x00000c480e602519 <Map>      0x0000247fc3102251 <FixedArray[0]>
0x35fd1e6a7318: 0x0000247fc3102251      0x000035fd1e6a7129 <SharedFunctionInfo f>
0x35fd1e6a7328: 0x000035fd1e683eb1 (context)     0x000035fd1e6a72e9
0x35fd1e6a7338: 0x0000337e72c1fe41 <Code BUILTIN>      0x0000247fc3102321

gdb-peda$ job 0x000035fd1e6a72e9
0x35fd1e6a72e9: [FeedbackCell] in OldSpace
 - map: 0x383e0b1835f1 <Map[16]>
 - one closure - value: 0x247fc31022e1 <undefined>

```

v8 6.7以后function的code不再可写

### JS array
![](IMG/v8_basic/JSArray.png)

### 参考

1. https://v8.dev/blog/fast-properties
2. ctf_study11 
3. [inline-cache](https://mrale.ph/blog/2012/06/03/explaining-js-vms-in-js-inline-caches.html)  ok
4. [v8介绍]https://blog.csdn.net/swimming_in_IT_/article/details/78869549 
5. [hidden class](https://richardartoul.github.io/jekyll/update/2015/04/26/hidden-classes.html)  ok

CTF题目
[rollad8-Anciety](https://www.anquanke.com/post/id/147829#h3-16)  

漏洞
https://mem2019.github.io/jekyll/update/2019/09/05/Problems-About-Expm1.html
https://abiondo.me/2019/01/02/exploiting-math-expm1-v8/#the-bug


### 后记
如何更好的解释一个事情内部原理
1. 抛弃一些例如要做什么不要做什么的建议，这样对理解没有帮助，会让人当成规则一样去遵守，而且规则会在不知不觉中就过时了。
2. 挑选正确的抽象层次，尤其是一些满是汇编的ppt