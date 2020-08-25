# clanrank
 适用于hoshinoBotV2的插件, 可以在QQ群中查询工会战排名. 

数据均来自Github@Kengxxiao

项目地址 https://github.com/Kengxxiao/Kyouka

网页在线查询 https://kengxxiao.github.io/Kyouka/

本插件以HoshinoV2为基础编写, 使用Hoshino v1请切换至v1分支。注意，v1版本可能无法得到及时更新和测试，如果您正在使用HoshinoBot的v1版本，并修改本插件使其适配v1，希望您能向本项目的v1分支提交Pull request.

如果发生400/441错误, 可能是更新了POST请求头, 请更新或等待更新



现已更新缓存机制，已假定网站更新比游戏内延迟12分钟，则每次查询的时间戳生命周期为42分钟，如果没有过期则只需要发送本机缓存的数据。请限制使用频率, 为了不给原作者服务器增加太大负担。查询其他公会排名以及排行榜还未进入缓存

例如缓存的上次查询的时间戳为下午3点，则下午3：42之前查询会发送本地数据，3：42之后查询会自动在线更新。
## 指令示例
### 查询所有公会（需开启服务：sv_query）
* 查询会长卢本伟, 查询会长名字包含卢本伟的公会的排名
* 查询公会卢本伟, 查询公会名字包含卢本伟的公会的排名
* 查询排名5000, 查看5000名的公会分数信息
### 查询自己公会（需开启服务：sv_push）
* 绑定公会12345567889，后加的是公会会长的ID
* 公会排名，查询本公会排名
## 使用方法
1. ~~加入其他模块中~~
    
    不再支持此方法，因为配置文件使用了以下路径来读写：
    ```
    ./hoshino/modules/clanrank/clanrank.json
    ```
2. 创建新目录, 作为一个单独的模块来控制. 切换到Hoshino的模组目录, 然后clone本项目:
    ```
    cd ~/HoshinoBot/hoshino/modules/
    git clone https://github.com/pcr/clanrank.git
    ```
    修改配置文件：在config中启用该模块. 操作方法为编辑Hoshino下的`__bot__.py`文件：
    ```
    nano ~/Hoshino/hoshino/config/__bot__.py
    ```
    在`MODULES_ON`中仿照格式添加项`'clanrank'`. 
3. HoshinoBot v1版本请直接克隆`v1`分支：
   ```
   git clone -b v1 https://github.com/pcr/clanrank.git
   ```
4. 更新请切换到对应目录后，使用git更新：
   ```
   git pull
   ```
   如果要更换分支：
   ```
   git checkout -b 本地分支名 origin/v1
   ```
## 更新日志：

v1分支不再单独发布更新日志，请参考主分支

