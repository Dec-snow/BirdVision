# -*- coding: utf-8 -*-
"""
数据库初始化种子数据脚本

功能说明：
- 导入 Flask app 和 db
- 在应用上下文中运行
- 定义 30 种常见中国鸟类的种子数据列表（BirdSpecies 对象）
- 包含中文名、英文名、学名、科、描述、栖息地、保护状态
- 如果数据库中已有数据则跳过（不重复插入）

使用方式：
  cd bird-vision
  python -m app.init_db
"""

from app import create_app, db
from app.models import BirdSpecies


def get_seed_data():
    """
    返回 30 种常见中国鸟类的种子数据列表

    每条数据包含：
    - name_cn: 中文名
    - name_en: 英文名
    - scientific_name: 学名
    - family: 科
    - description: 描述（至少30字）
    - habitat: 栖息地（至少10字）
    - conservation_status: 保护状态
    """
    return [
        BirdSpecies(
            name_cn='麻雀',
            name_en='Eurasian Tree Sparrow',
            scientific_name='Passer montanus',
            family='雀科',
            description='麻雀是体型较小的雀形目鸟类，体长约14厘米，头顶和背部棕褐色，脸颊有白色斑块，喉部黑色。它们是典型的人居伴生鸟类，适应力极强，以谷物种子和小型昆虫为食，繁殖期会大量捕食农业害虫。',
            habitat='城市居民区、乡村农田、灌丛和草地',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='喜鹊',
            name_en='Common Magpie',
            scientific_name='Pica pica',
            family='鸦科',
            description='喜鹊是鸦科中型鸟类，体长约45厘米，头部和背部黑色带蓝绿金属光泽，腹部白色，长尾呈楔形。在中国传统文化中象征吉祥和好运，是少数能通过镜像测试的鸟类，非常聪明。',
            habitat='城市公园、乡村田野、山地林缘',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='白头鹎',
            name_en='Chinese Bulbul',
            scientific_name='Pycnonotus sinensis',
            family='鹎科',
            description='白头鹎是鹎科小型鸣禽，体长约18-20厘米，头顶后部有白色区域，上体灰褐色，腹部黄白色。食性杂，以浆果、水果和昆虫为食，是中国东部和南部城市中最常见的鸟类之一。',
            habitat='城市公园、居民区绿化带、行道树林',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='珠颈斑鸠',
            name_en='Spotted Dove',
            scientific_name='Spilopelia chinensis',
            family='鸠鸽科',
            description='珠颈斑鸠是鸠鸽科中型鸟类，体长约30厘米，颈部两侧有黑色带白色斑点的半环状图案，如同珍珠项链。全身粉灰褐色，叫声低沉而有节奏，巢穴简陋，仅由几根树枝搭成。',
            habitat='城市公园、居民区、农田和乡村',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='家燕',
            name_en='Barn Swallow',
            scientific_name='Hirundo rustica',
            family='燕科',
            description='家燕是燕科常见候鸟，体长约15-19厘米，背部深蓝色带金属光泽，腹部白色，尾羽深叉形。每年春季从东南亚迁徙至中国繁殖，用泥巴在屋檐下筑造半碗状泥巢，是出色的空中捕虫能手。',
            habitat='人类居住区屋檐下、农田上空、水域附近',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='翠鸟',
            name_en='Common Kingfisher',
            scientific_name='Alcedo atthis',
            family='翠鸟科',
            description='翠鸟是翠鸟科小型鸟类，体长仅15-17厘米，背部和翼羽呈亮蓝色带金属光泽，腹部橙红色，喙长而直。常静栖于水边低枝上，发现鱼虾后以极快速度俯冲入水捕食，成功率极高。',
            habitat='溪流、河流、湖泊和池塘岸边',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='白鹭',
            name_en='Little Egret',
            scientific_name='Egretta garzetta',
            family='鹭科',
            description='白鹭是鹭科白鹭属鸟类，体长约55厘米，全身洁白，繁殖期枕部有两根长形蓑羽，背部也有装饰性蓑羽。嘴和脚均为黑色，是中国分布最广的鹭科鸟类，常成群在浅水中缓慢行走觅食。',
            habitat='河流、湖泊、稻田、沼泽和沿海湿地',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='池鹭',
            name_en='Chinese Pond Heron',
            scientific_name='Ardeola bacchus',
            family='鹭科',
            description='池鹭是鹭科中小型涉禽，体长约40-50厘米，繁殖期头部和背部呈栗红色，翅膀蓝灰色，腹部白色，非繁殖期全身变为灰褐色带细密斑纹。常在池塘和水田中涉水觅食。',
            habitat='池塘、水田、溪流和沼泽湿地',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='普通翠鸟',
            name_en='Common Kingfisher',
            scientific_name='Alcedo atthis',
            family='翠鸟科',
            description='普通翠鸟是翠鸟科最具代表性的种类，体型小巧玲珑，羽毛色彩鲜艳夺目。背部翠蓝色带金属光泽，腹部橙红色，嘴粗直呈黑色。以鱼虾和水生昆虫为主食，在土崖上挖洞筑巢。',
            habitat='山间溪流、平原河流、湖泊和池塘',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='戴胜',
            name_en='Eurasian Hoopoe',
            scientific_name='Upupa epops',
            family='戴胜科',
            description='戴胜是戴胜科唯一的现存物种，体长约26-28厘米，最显著特征是头上华丽的扇形橙棕色冠羽。全身粉棕色，翅膀黑白相间，喙细长微弯，以地面昆虫为主要食物。',
            habitat='开阔农田、草地、果园和村庄附近',
            conservation_status='国家二级保护动物'
        ),
        BirdSpecies(
            name_cn='啄木鸟',
            name_en='Great Spotted Woodpecker',
            scientific_name='Dendrocopos major',
            family='啄木鸟科',
            description='大斑啄木鸟是啄木鸟科常见种类，体长约23厘米，上体黑白相间，腹部白色，臀部红色。头骨结构特殊，能有效缓冲啄木冲击力，舌骨细长带倒钩，擅长在树干上啄食蛀虫。',
            habitat='各类森林、林地、公园和果园',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='红嘴蓝鹊',
            name_en='Red-billed Blue Magpie',
            scientific_name='Urocissa erythrorhyncha',
            family='鸦科',
            description='红嘴蓝鹊是鸦科大型鸟类，体长55-65厘米，加上尾羽可达近一米。鲜红色的大嘴和脚、蓝色长尾羽、白色头顶斑纹是最显著的特征。常成群活动于山地林间，叫声响亮粗犷。',
            habitat='山地针阔混交林和常绿阔叶林',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='灰喜鹊',
            name_en='Azure-winged Magpie',
            scientific_name='Cyanopica cyanus',
            family='鸦科',
            description='灰喜鹊是鸦科中型鸟类，体长约33-40厘米，头顶、翅膀和长尾呈天蓝色，腹部浅灰色。常成群活动于针叶林和混交林中，群内成员会协作驱赶入侵猛禽，具有重要的生态价值。',
            habitat='针叶林、针阔混交林和公园',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='乌鸦',
            name_en='Large-billed Crow',
            scientific_name='Corvus macrorhynchos',
            family='鸦科',
            description='大嘴乌鸦是鸦科大型鸟类，体长约50厘米，全身黑色带有紫蓝色光泽。乌鸦是鸟类中智力水平最高的类群之一，能使用工具、理解物理原理、记住人类面孔，具有重要的科学研究价值。',
            habitat='城市、乡村、农田和山地林缘',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='画眉',
            name_en='Hwamei',
            scientific_name='Garrulax canorus',
            family='噪眉科',
            description='画眉是噪眉科中型鸟类，体长约22-24厘米，眼部有一条白色眉纹如同画出的眉毛。以悦耳多变的鸣叫声闻名于世，能发出多种旋律婉转的鸣唱，自古以来就是传统笼养观赏鸟中的名品。',
            habitat='南方低山丘陵、灌丛和竹林',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='杜鹃',
            name_en='Common Cuckoo',
            scientific_name='Cuculus canorus',
            family='杜鹃科',
            description='杜鹃又称布谷鸟，以独特的巢寄生繁殖策略闻名。雌鸟将卵产在其他鸟类巢中，让寄主代为孵化育雏。雏鸟出壳后会本能地将寄主的卵推出巢外独占资源。叫声"布谷-布谷"与农事节气息息相关。',
            habitat='森林边缘、农田和灌丛',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='布谷鸟',
            name_en='Common Cuckoo',
            scientific_name='Cuculus canorus',
            family='杜鹃科',
            description='布谷鸟即杜鹃的俗称，是夏候鸟，春夏从南亚和非洲迁徙至中国繁殖。体型适中，羽毛灰褐色带有条纹，外形似小型猛禽。其巢寄生行为是动物行为学研究的经典案例，在生态系统中控制某些昆虫种群数量。',
            habitat='林地边缘、农田、草地和灌丛',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='鸳鸯',
            name_en='Mandarin Duck',
            scientific_name='Aix galericulata',
            family='鸭科',
            description='鸳鸯是鸭科中小型游禽，雄鸟羽毛极为华丽，头部翠绿色冠羽，背部褐色带金属光泽，两翼有橙黄色帆状翅羽。在中国传统文化中象征忠贞不渝的爱情，实际配对关系并非终身制。',
            habitat='山地溪流、湖泊、池塘和沼泽',
            conservation_status='国家二级保护动物'
        ),
        BirdSpecies(
            name_cn='绿头鸭',
            name_en='Mallard',
            scientific_name='Anas platyrhynchos',
            family='鸭科',
            description='绿头鸭是家鸭的野生祖先，体长50-65厘米。雄鸟头部亮绿色带金属光泽，颈部有白色环纹，尾羽中央两枚黑色向上卷曲。雌鸟棕褐色，两者均有蓝色翼镜。是中国分布最广的鸭类之一。',
            habitat='湖泊、河流、池塘、水库和沿海湿地',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='丹顶鹤',
            name_en='Red-crowned Crane',
            scientific_name='Grus japonensis',
            family='鹤科',
            description='丹顶鹤是鹤科大型涉禽，体长约150厘米，翼展可达240厘米。全身白色，颈部和飞羽末端黑色，头顶裸露部分鲜红色如同皇冠。一夫一妻制，是东亚地区最具文化象征意义的鸟类之一。',
            habitat='东北沼泽湿地、长江中下游湖泊湿地',
            conservation_status='国家一级保护动物'
        ),
        BirdSpecies(
            name_cn='朱鹮',
            name_en='Crested Ibis',
            scientific_name='Nipponia nippon',
            family='鹮科',
            description='朱鹮被称为"东方宝石"，全身白色，翅膀和尾羽飞羽呈朱红色，面部裸露皮肤红色。1981年仅存7只野生个体，经四十余年保护种群恢复至数千只，是濒危物种保护的成功典范。',
            habitat='陕西洋县等地水田、沼泽和山地溪流',
            conservation_status='国家一级保护动物'
        ),
        BirdSpecies(
            name_cn='红腹锦鸡',
            name_en='Golden Pheasant',
            scientific_name='Chrysolophus pictus',
            family='雉科',
            description='红腹锦鸡是中国特有雉类，雄鸟体长约100厘米，外形极为华丽。头顶金色丝状冠羽，后颈橙棕色扇状羽被，上体金色带黑色横斑，下体深红色。是中国传统文化中吉祥富贵的象征。',
            habitat='甘肃、陕西、四川等地的山地森林',
            conservation_status='国家二级保护动物'
        ),
        BirdSpecies(
            name_cn='白鹇',
            name_en='Silver Pheasant',
            scientific_name='Lophura nycthemera',
            family='雉科',
            description='白鹇是大型鸡类，雄鸟体长100-130厘米，上体和尾羽白色布满V字形黑色波纹，面部红色，头顶黑色冠羽。求偶时展开华丽白色尾羽如扇面般壮观，一夫多妻制，日间在地面活动。',
            habitat='南方海拔200-2000米常绿阔叶林',
            conservation_status='国家二级保护动物'
        ),
        BirdSpecies(
            name_cn='黑脸琵鹭',
            name_en='Black-faced Spoonbill',
            scientific_name='Platalea minor',
            family='鹮科',
            description='黑脸琵鹭是全球最濒危的鸟类之一，全球仅约6000只。体长70-80厘米，全身白色，脸部裸露皮肤黑色，喙扁平如琵琶状。繁殖于朝鲜半岛和辽东半岛，越冬于中国台湾、香港等地。',
            habitat='海岸湿地、河口泥滩和浅水区域',
            conservation_status='国家一级保护动物'
        ),
        BirdSpecies(
            name_cn='大天鹅',
            name_en='Whooper Swan',
            scientific_name='Cygnus cygnus',
            family='鸭科',
            description='大天鹅是鸭科天鹅属大型水鸟，体长120-160厘米，翼展超2米。全身洁白，喙黑色基部有大面积黄色。是中国最大的水鸟之一，冬季从西伯利亚迁徙至中国中南部湖泊湿地越冬。',
            habitat='北方繁殖地湖泊、南方越冬地湿地',
            conservation_status='国家二级保护动物'
        ),
        BirdSpecies(
            name_cn='白头鹤',
            name_en='Hooded Crane',
            scientific_name='Grus monacha',
            family='鹤科',
            description='白头鹤是全球最濒危的鹤类之一，全球约15000只。体长约100厘米，头部和颈部白色，前额有红色裸露皮肤，身体深灰色。繁殖于俄罗斯远东和中国东北沼泽湿地。',
            habitat='东北沼泽湿地、长江中下游越冬地',
            conservation_status='国家一级保护动物'
        ),
        BirdSpecies(
            name_cn='苍鹭',
            name_en='Grey Heron',
            scientific_name='Ardea cinerea',
            family='鹭科',
            description='苍鹭是大型鹭类，体长约90-100厘米，外形瘦长。全身灰蓝色，头顶黑色，前颈和胸部有黑色纵纹。常长时间静止站立于浅水中耐心等待猎物，因此有"老等"的俗称，以鱼类和蛙类为食。',
            habitat='大型湖泊、河流、水库和沿海湿地',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='夜鹭',
            name_en='Black-crowned Night Heron',
            scientific_name='Nycticorax nycticorax',
            family='鹭科',
            description='夜鹭是中型涉禽，体长约50-60厘米，成鸟蓝灰色，头顶有白色冠羽，虹膜红色。主要在黄昏和夜间活动，红色眼睛是适应夜行生活的重要特征。适应力强，城市公园池塘中也能生存繁殖。',
            habitat='城市公园、池塘、河流和湿地',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='黄鹂',
            name_en='Black-naped Oriole',
            scientific_name='Oriolus chinensis',
            family='黄鹂科',
            description='黑枕黄鹂体长约25-28厘米，雄鸟通体金黄色，头部两侧有黑色宽纹延伸至枕部相连。鸣叫声清脆悦耳，是中国传统文化中最受赞美的鸟鸣之一，唐代杜甫"两个黄鹂鸣翠柳"使其成为春天的象征。',
            habitat='阔叶林、公园和村落附近高大树木',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='伯劳',
            name_en='Bull-headed Shrike',
            scientific_name='Lanius bucephalus',
            family='伯劳科',
            description='伯劳是伯劳科中型鸣禽，体长约18-25厘米，被称为"雀形目中的猛禽"。最独特的行为是将猎物刺挂在荆棘或铁丝网上储存和撕食。喙上喙尖端有齿状突起，能捕食大型昆虫甚至小型鸟类。',
            habitat='农田边缘、灌木丛和林缘开阔地带',
            conservation_status='三有保护动物'
        ),
        # ---- 以下为扩展物种（20种） ----
        BirdSpecies(
            name_cn='红耳鹎',
            name_en='Red-whiskered Bulbul',
            scientific_name='Pycnonotus jocosus',
            family='鹎科',
            description='红耳鹎是鹎科鸣禽，体长约20厘米。头顶有醒目的黑色高冠羽，耳羽红色，眼下有红色斑点，上体暗褐色，腹部灰白色。性情活泼好动，常在树冠层和灌丛中跳跃觅食果实和昆虫，鸣叫声明亮多变。',
            habitat='城市公园、居民区绿化带和低山灌丛',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='乌鸫',
            name_en='Common Blackbird',
            scientific_name='Turdus merula',
            family='鸫科',
            description='乌鸫是鸫科中型鸣禽，体长约25厘米。雄鸟全身黑色，喙和眼圈橙黄色，雌鸟深褐色。鸣唱婉转多变，能模仿其他鸟类的叫声，被誉为"百舌鸟"。以蚯蚓、昆虫和浆果为食，常在草坪上觅食。',
            habitat='城市公园、园林绿地和阔叶林',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='八哥',
            name_en='Crested Myna',
            scientific_name='Acridotheres cristatellus',
            family='椋鸟科',
            description='八哥是椋鸟科中型鸟类，体长约26厘米。全身黑色带紫蓝色金属光泽，前额有明显的黑色冠羽，飞行时可见白色翼斑。善于模仿人语和各类声音，是中国最著名的笼养鸣禽之一，已被列入保护名录。',
            habitat='城市公园、乡村农地和开阔林地',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='丝光椋鸟',
            name_en='Red-billed Starling',
            scientific_name='Spodiopsar sericeus',
            family='椋鸟科',
            description='丝光椋鸟又称丝光鸟，体长约24厘米。雄鸟头部灰白色，喉部银灰色如丝绸光泽，背部深灰褐色，喙红色。秋冬季节常集成数百只大群在城市行道树上栖息，场面十分壮观。以果实和昆虫为主食。',
            habitat='城市公园、行道树、果园和农田',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='金翅雀',
            name_en='Grey-capped Greenfinch',
            scientific_name='Chloris sinica',
            family='燕雀科',
            description='金翅雀是燕雀科小型鸣禽，体长约14厘米。上体橄榄绿色，翅膀有鲜明的金黄色翼斑，飞行时尤为抢眼。鸣声清脆悦耳如银铃，常在枝头边飞边鸣。以植物种子为主食，秋冬集小群活动。',
            habitat='平原农田、果园、公园和灌丛',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='大山雀',
            name_en='Great Tit',
            scientific_name='Parus major',
            family='山雀科',
            description='大山雀是山雀科的小型鸣禽，体长约13-15厘米。头部黑色，脸颊有大块白色斑，腹部中央有黑色纵纹。极为活跃好动，常在枝头倒挂觅食，以昆虫和种子为食，是重要的农林益鸟。',
            habitat='各类林地、公园、果园和城市绿化',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='红胁蓝尾鸲',
            name_en='Red-flanked Bluetail',
            scientific_name='Tarsiger cyanurus',
            family='鸫科',
            description='红胁蓝尾鸲是鸫科小型鸣禽，体长约13-15厘米。雄鸟上体深蓝色，两胁橙红色，腹部白色。雌鸟上体棕褐色，尾羽蓝色。迁徙季节常出现在城市公园灌丛中，静立时不断抖动尾羽。',
            habitat='针叶林、混交林和迁徙途中的公园灌丛',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='白鹡鸰',
            name_en='White Wagtail',
            scientific_name='Motacilla alba',
            family='鹡鸰科',
            description='白鹡鸰是鹡鸰科小型鸣禽，体长约18厘米。全身黑白灰三色搭配简洁优雅，飞行路线呈波浪形。最显著的特征是走路时尾部不停上下摆动。常在地面和水边活动，以昆虫和水生无脊椎动物为食。',
            habitat='河流、湖泊岸边、水田和城市草坪',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='黑水鸡',
            name_en='Common Moorhen',
            scientific_name='Gallinula chloropus',
            family='秧鸡科',
            description='黑水鸡是秧鸡科中型涉禽，体长约30-35厘米。全身灰黑色，额甲鲜红色，尾下覆羽白色，趾长无蹼。善游泳和潜水，受惊时迅速躲入芦苇丛中。以水生植物、小鱼虾和水生昆虫为食。',
            habitat='池塘、湖泊、水库和城市公园水域',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='小䴙䴘',
            name_en='Little Grebe',
            scientific_name='Tachybaptus ruficollis',
            family='䴙䴘科',
            description='小䴙䴘（音pì tī）是䴙䴘科小型游禽，体长约25-29厘米。繁殖期颈侧栗红色，嘴角有黄斑，非繁殖期全身灰褐色。极善潜水和游泳，受惊时能长时间潜藏于水下仅露出喙尖，以小鱼虾和水生昆虫为食。',
            habitat='池塘、湖泊、水库和缓流河道',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='斑鱼狗',
            name_en='Pied Kingfisher',
            scientific_name='Ceryle rudis',
            family='翠鸟科',
            description='斑鱼狗是翠鸟科中型鸟类，体长约25-29厘米。羽毛黑白斑驳，雄鸟胸部有两条黑色横纹。具有独特的悬停捕鱼技巧，能在水面以上10-20米处振翅悬停，锁定猎物后垂直俯冲入水，捕食效率极高。',
            habitat='河流、湖泊、水库和大型池塘',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='褐马鸡',
            name_en='Brown Eared Pheasant',
            scientific_name='Crossoptilon mantchuricum',
            family='雉科',
            description='褐马鸡是中国特有珍稀雉类，体长约100厘米。全身深褐色，耳羽簇白色向后竖起如双角，尾羽蓬松上翘。仅分布于山西、河北等地，数量稀少，被列为国家一级保护动物，中国鸟类学会的会徽图案即为此鸟。',
            habitat='山西、河北海拔1500-2500米山地针阔混交林',
            conservation_status='国家一级保护动物'
        ),
        BirdSpecies(
            name_cn='白冠长尾雉',
            name_en="Reeves's Pheasant",
            scientific_name='Syrmaticus reevesii',
            family='雉科',
            description='白冠长尾雉是中国特有雉类，雄鸟体长可达210厘米，其中尾羽长达150厘米以上，是尾羽最长的鸟类之一。头顶白色，上体棕黄色带黑白斑纹，尾羽银灰色带黑色横斑。因栖息地破坏和偷猎，种群数量急剧下降。',
            habitat='华中地区海拔300-1800米山地森林',
            conservation_status='国家一级保护动物'
        ),
        BirdSpecies(
            name_cn='中华秋沙鸭',
            name_en='Scaly-sided Merganser',
            scientific_name='Mergus squamatus',
            family='鸭科',
            description='中华秋沙鸭是全球最濒危的鸭科鸟类之一，全球仅存约3000只。雄鸟头部和上颈墨绿色带金属光泽，体侧有鳞片状灰色斑纹，喙窄长带锯齿。对水质要求极高，被称为"水质试金石"，主要繁殖于中国东北原始森林中的溪流。',
            habitat='东北原始林区溪流、长江以南清澈水域越冬',
            conservation_status='国家一级保护动物'
        ),
        BirdSpecies(
            name_cn='东方白鹳',
            name_en='Oriental Stork',
            scientific_name='Ciconia boyciana',
            family='鹳科',
            description='东方白鹳是鹳科大型涉禽，体长约110-120厘米，翼展可达220厘米。全身白色，飞羽黑色，喙粗长呈黑色，眼周红色。全球仅存约3000只，是IUCN红色名录濒危物种，繁殖于中国东北和俄罗斯远东湿地。',
            habitat='东北湿地繁殖、长江中下游湖泊湿地越冬',
            conservation_status='国家一级保护动物'
        ),
        BirdSpecies(
            name_cn='白琵鹭',
            name_en='Eurasian Spoonbill',
            scientific_name='Platalea leucorodia',
            family='鹮科',
            description='白琵鹭是鹮科大型涉禽，体长约80-90厘米。全身白色，喙长而扁，前端扩大呈琵琶状。觅食时将喙伸入水中左右摆动，利用触觉感知猎物。常与黑脸琵鹭混群活动，是国家二级保护动物。',
            habitat='浅水湖泊、河流滩涂和沿海湿地',
            conservation_status='国家二级保护动物'
        ),
        BirdSpecies(
            name_cn='鸿雁',
            name_en='Swan Goose',
            scientific_name='Anser cygnoides',
            family='鸭科',
            description='鸿雁是鸭科雁属大型游禽，体长约80-90厘米，是家鹅的野生祖先。上体灰褐色，前颈和胸部浅棕色，喙黑色基部有白色细环。迁徙时排成"人"字形或"一"字形队列，是古代书信"鸿雁传书"的由来。',
            habitat='北方草原湖泊繁殖、长江中下游湿地越冬',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='赤麻鸭',
            name_en='Ruddy Shelduck',
            scientific_name='Tadorna ferruginea',
            family='鸭科',
            description='赤麻鸭是鸭科中型游禽，体长约60-70厘米。全身橙棕色，雄鸟繁殖期颈部有黑色环纹，飞行时可见翅膀上黑白绿三色翼镜。在中国传统文化中被称为"鸳鸯"的古称，是忠诚的一夫一妻制鸟类。',
            habitat='高原湖泊、河流和开阔湿地',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='环颈雉',
            name_en='Common Pheasant',
            scientific_name='Phasianus colchicus',
            family='雉科',
            description='环颈雉俗称野鸡，是雉科最常见的野生鸡类。雄鸟体长约70-90厘米，全身色彩斑斓，头部金属绿色，颈部有白色环纹，尾羽长而有横斑。是中国分布最广的猎禽，也是许多地方亚种的祖先种群。',
            habitat='农田、草地、灌丛和林缘地带',
            conservation_status='三有保护动物'
        ),
        BirdSpecies(
            name_cn='灰鹤',
            name_en='Common Crane',
            scientific_name='Grus grus',
            family='鹤科',
            description='灰鹤是鹤科大型涉禽，体长约100-120厘米。全身灰色，头部和上颈黑色，眼后至颈侧有白色条纹，头顶红色裸露皮肤。迁徙时在中国北方和中部地区大量集群停歇，数量达数万只。',
            habitat='北方沼泽湿地繁殖、中南部湿地越冬',
            conservation_status='国家二级保护动物'
        ),
    ]


def init_db():
    """
    执行数据库初始化：
    - 创建所有数据表
    - 检查是否已有数据，如无则插入种子数据
    """
    # 创建 Flask 应用实例
    app = create_app()

    # 在应用上下文中执行数据库操作
    with app.app_context():
        # 创建所有数据表（如果不存在）
        db.create_all()
        print('[信息] 数据库表创建完成（如已存在则跳过）')

        # 检查数据库中是否已有 BirdSpecies 数据
        existing_count = BirdSpecies.query.count()
        if existing_count > 0:
            print(f'[信息] 数据库中已有 {existing_count} 条鸟类数据，跳过种子数据插入')
            return

        # 获取种子数据
        seed_birds = get_seed_data()

        # 批量插入种子数据
        db.session.add_all(seed_birds)
        db.session.commit()

        print(f'[完成] 成功插入 {len(seed_birds)} 条鸟类种子数据')

        # 打印插入的鸟类名称列表
        print('[信息] 已插入的鸟类列表：')
        for i, bird in enumerate(seed_birds, 1):
            print(f'  {i:2d}. {bird.name_cn} ({bird.scientific_name}) - {bird.family}')


if __name__ == '__main__':
    init_db()
