# clanrank
 适用于hoshinoBotV1的插件, 可以在QQ群中查询工会战排名. 

最后更新时间：2020年7月3日下午15时
数据均来自Github@Kengxxiao
项目地址 https://github.com/Kengxxiao/Kyouka
网页在线查询 https://kengxxiao.github.io/Kyouka/
本插件以HoshinoV1为基础编写, 使用HoshinoV2应当对服务层进行修改. 
请限制使用频率, 为了不给原作者服务器增加太大负担. 
## 指令示例
* 会长排名卢本伟, 查询会长名字包含卢本伟的公会的排名
* 公会排名卢本伟, 查询公会名字包含卢本伟的公会的排名
* 查看排名5000, 查看5000名的公会分数信息
* 分数排名274085737, 查看该分数对应的排名信息

## 使用方法
1. 将文件`clanrank.py`放到Hoshino/hoshino/modules之下的一个目录内即可, 请放到已开启的模块中, 在Hoshino目录下的`config.py`中可以查看已开启的模块. 
2. 创建新目录, 作为一个单独的模块来控制. 切换到Hoshino的模组目录, 然后直接使用git clone:
    ```
    cd ~Hoshino/hoshino/modules/
    git clone https://github.com/VikingXie1999/clanrank.git
    ```
    当选择创建新目录时, 同时应当在config.py中启用该模块. 操作方法为编辑Hoshino下的`config.py`文件：
    ```
    nano ~/Hoshino/config.py
    ```
    在`MODULES_ON`中仿照格式添加项`'clanrank'`. 
3. 如果发生400错误, 可能是更新了POST请求头, 请更新, 在切换到对应目录后使用：
    ```
    git pull origin master
    ```
## 更新日志：
### v0.0.3
更新时间：2020/7/3 下午3:05:52
* 更新请求, 为所有查询时的POST请求添加"history"
* 添加了对BadRequest的处理, 可以半夜被叫起来修服务器

### v0.0.2
更新时间：2020/7/1 上午12:22:19
* 更新请求, 为请求头添加"Referer"

### v0.0.1
更新时间：2020/6/30 下午2:19:04
* 初版发布, 支持四种查询模式

