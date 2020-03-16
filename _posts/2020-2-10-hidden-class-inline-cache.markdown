---
layout: post
title:  "hidden-class 和 inline cache"
categories: browser
tags: browser
excerpt: v8 基础
mathjax: true
---

* content
{:toc}

### Overview 

javascript 是一门动态编程语言，可以随时添加或删除属性(运行中也可以)，需要在hash表中查找property,但是这样速度很慢
因此引入hidden class 和 Inline caching 
### hidden class

通过固定偏移查找对象中的property
javascript 中 用函数模拟表达类定义
```c
function Point(x,y){
    this.x=x;
    this.y=y;
}
var p1 = new Point(1,2);
var p2 = new Point(1,2);
```

![hidden-class](IMG/hidden-class/hidden1.png)

```
gdb-peda$ job 0x1084048cded1
0x1084048cded1: [JS_OBJECT_TYPE]
 - map: 0x180873fcac79 <Map(HOLEY_ELEMENTS)> [FastProperties]
 - prototype: 0x1084048cddd1 <Object map = 0x180873fcacc9>
 - elements: 0x07e84e700c71 <FixedArray[0]> [HOLEY_ELEMENTS]
 - properties: 0x07e84e700c71 <FixedArray[0]> {
    #x: 1 (const data field 0)
    #y: 2 (const data field 1)
 }
gdb-peda$ job 0x1084048cdfe9
0x1084048cdfe9: [JS_OBJECT_TYPE]
 - map: 0x180873fcac79 <Map(HOLEY_ELEMENTS)> [FastProperties]
 - prototype: 0x1084048cddd1 <Object map = 0x180873fcacc9>
 - elements: 0x07e84e700c71 <FixedArray[0]> [HOLEY_ELEMENTS]
 - properties: 0x07e84e700c71 <FixedArray[0]> {
    #x: 1 (const data field 0)
    #y: 2 (const data field 1)
 }
```
p1 和p2 的map和properties 都一样

```

gdb-peda$ job 0x180873fcac79    // [ c2 ]
0x180873fcac79: [Map]
 - type: JS_OBJECT_TYPE
 - instance size: 104
 - inobject properties: 10
 - elements kind: HOLEY_ELEMENTS
 - unused property fields: 8
 - enum length: invalid
 - stable_map
 
 - back pointer: 0x180873fcac29 <Map(HOLEY_ELEMENTS)>  // 指向c1

 - prototype_validity cell: 0x11593229f8c1 <Cell value= 0>
 - instance descriptors (own) #2: 0x1084048cdfa1 <DescriptorArray[2]>
 - layout descriptor: (nil)
 - prototype: 0x1084048cddd1 <Object map = 0x180873fcacc9>
 - constructor: 0x11593229f631 <JSFunction Point (sfi = 0x11593229f3b9)>
 - dependent code: 0x07e84e7002c1 <Other heap object (WEAK_FIXED_ARRAY_TYPE)>
 - construction counter: 6
gdb-peda$ job 0x180873fcac29   // [ c1 ]
0x180873fcac29: [Map]
 - type: JS_OBJECT_TYPE
 - instance size: 104
 - inobject properties: 10
 - elements kind: HOLEY_ELEMENTS
 - unused property fields: 9
 - enum length: invalid
 - back pointer: 0x180873fcaae9 <Map(HOLEY_ELEMENTS)> // 指向c0
 - prototype_validity cell: 0x11593229f8c1 <Cell value= 0>
 - instance descriptors #1: 0x1084048cdfa1 <DescriptorArray[2]>
 - layout descriptor: (nil)
 - transitions #1: 0x180873fcac79 <Map(HOLEY_ELEMENTS)>
     #y: (transition to (const data field, attrs: [WEC]) @ Any) -> 0x180873fcac79 <Map(HOLEY_ELEMENTS)>
 - prototype: 0x1084048cddd1 <Object map = 0x180873fcacc9>
 - constructor: 0x11593229f631 <JSFunction Point (sfi = 0x11593229f3b9)>
 - dependent code: 0x07e84e7002c1 <Other heap object (WEAK_FIXED_ARRAY_TYPE)>
 - construction counter: 6
gdb-peda$ job 0x180873fcaae9   // [ c0 ]
0x180873fcaae9: [Map]
 - type: JS_OBJECT_TYPE
 - instance size: 104
 - inobject properties: 10
 - elements kind: HOLEY_ELEMENTS
 - unused property fields: 10
 - enum length: invalid
 - back pointer: 0x07e84e7004d1 <undefined>
 - prototype_validity cell: 0x009770940609 <Cell value= 1>
 - instance descriptors (own) #0: 0x07e84e700259 <DescriptorArray[0]>
 - layout descriptor: (nil)
 - transitions #1: 0x180873fcac29 <Map(HOLEY_ELEMENTS)>  // 指向c1
     #x: (transition to (const data field, attrs: [WEC]) @ Any) -> 0x180873fcac29 <Map(HOLEY_ELEMENTS)>
 - prototype: 0x1084048cddd1 <Object map = 0x180873fcacc9>
 - constructor: 0x11593229f631 <JSFunction Point (sfi = 0x11593229f3b9)>
 - dependent code: 0x07e84e7002c1 <Other heap object (WEAK_FIXED_ARRAY_TYPE)>
 - construction counter: 5
```

追踪map, back pointer 和transitions 就像两个链表指针，将c0,c1,c2 串联起来
* 开始处于c2 状态 back pointer 指向c1 .
* c1 中存在transitions 指向c2 ,  back pointer 指向c0 . 
* c0 的transitions 指向c1 ,  back pointer 指向 <undefined>

#### 添加property 

```
function Point(x,y){
    this.x=x;
    this.y=y;
}
var p1 = new Point(1,2);
var p2 = new Point(1,2);
%DebugPrint(p1);
%DebugPrint(p2);
%SystemBreak();
p2.n = 4 ;
%DebugPrint(p1);
%DebugPrint(p2);
%SystemBreak();
```
添加了p2.n 属性，从c2 演化出c3
c3 back pointer 指向c2 
c2 的transitions 指向c3 ，表明多出一个property n


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

有以下4种状态
* Premonomorphic 只通过一次 没有开始IC
* Monomorphic  一个IC
* Polymorphic  多个IC 快
* Megamorphi   多个IC 慢

调试(--trace-ic)
