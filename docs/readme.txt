me.blog
=======

2014.01.21
----------

    1. python以目录来组织模块, 就是所谓的包. 用包的一大好处: 可以解决名字空间冲突的问题, 即文件重名问题.
    下面主要说3点:
    1). 如何使一个目录变成包,如何import
           目录下放一个__init__.py文件(内容可以为空), import包内模块的时候使用"."分割, 比如import Apackage.Amodule
    2). __init__.py的__all__变量
           __all__指定的是指此包被import * 的时候, 哪些模块会被import进来
    3). __init__.py的__path__变量
           __path__指定了包的搜索路径

2013.12.20
----------

    1. 分离出model
    tag 2013.12.20.before.update.model

    2.
    app.config["OwnerEmail"] = "deepgully@gmail.com"
    app.config["DefaultPassword"] = "admin"

2013.12.19
-----------

    1. werkzeug

    2. alembic

    --END
