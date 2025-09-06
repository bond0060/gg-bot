#!/usr/bin/env python3
"""Test enhanced city classification system with hotel data mapping"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.city_classifier import city_classifier

def test_city_classification():
    """Test city classification with hotel data mapping"""
    
    # Test cases: (city_name, expected_tier, expected_hotel_count_range)
    test_cases = [
        # A类城市测试
        ("上海", "A", (1000, 3000)),
        ("东京", "A", (1000, 3000)),
        ("曼谷", "A", (1000, 2000)),
        ("新加坡", "A", (800, 1500)),
        ("香港", "A", (800, 1200)),
        ("首尔", "A", (600, 1200)),
        ("台北", "A", (600, 1000)),
        ("北京", "A", (1000, 3000)),
        ("深圳", "A", (800, 1500)),
        ("广州", "A", (800, 1200)),
        ("纽约", "A", (1000, 2000)),
        ("伦敦", "A", (800, 1500)),
        ("巴黎", "A", (800, 1200)),
        ("洛杉矶", "A", (600, 1000)),
        ("悉尼", "A", (400, 800)),
        ("迪拜", "A", (500, 1000)),
        ("阿布扎比", "A", (400, 800)),
        
        # B类城市测试
        ("清迈", "B", (200, 600)),
        ("武汉", "B", (200, 400)),
        ("名古屋", "B", (150, 350)),
        ("大阪", "B", (300, 500)),
        ("京都", "B", (200, 400)),
        ("福冈", "B", (100, 300)),
        ("札幌", "B", (100, 200)),
        ("成都", "B", (300, 500)),
        ("杭州", "B", (250, 450)),
        ("南京", "B", (200, 400)),
        ("西安", "B", (150, 350)),
        ("青岛", "B", (100, 300)),
        ("大连", "B", (100, 250)),
        ("厦门", "B", (100, 200)),
        ("苏州", "B", (150, 300)),
        ("无锡", "B", (80, 150)),
        ("宁波", "B", (80, 150)),
        ("温州", "B", (60, 120)),
        ("佛山", "B", (70, 120)),
        ("东莞", "B", (80, 150)),
        ("中山", "B", (40, 80)),
        ("珠海", "B", (60, 120)),
        ("惠州", "B", (50, 100)),
        ("江门", "B", (30, 60)),
        ("肇庆", "B", (25, 50)),
        ("湛江", "B", (30, 60)),
        ("茂名", "B", (20, 40)),
        ("阳江", "B", (15, 35)),
        ("清远", "B", (15, 30)),
        ("韶关", "B", (10, 25)),
        ("河源", "B", (10, 20)),
        ("梅州", "B", (10, 25)),
        ("汕尾", "B", (8, 20)),
        ("汕头", "B", (25, 50)),
        ("潮州", "B", (10, 20)),
        ("揭阳", "B", (8, 15)),
        ("云浮", "B", (5, 15)),
        ("巴厘岛", "B", (200, 400)),
        ("普吉岛", "B", (150, 300)),
        ("苏梅岛", "B", (80, 150)),
        ("甲米", "B", (60, 120)),
        ("华欣", "B", (40, 80)),
        ("芭提雅", "B", (80, 150)),
        ("清莱", "B", (30, 60)),
        ("素可泰", "B", (15, 30)),
        ("大城", "B", (10, 25)),
        ("华富里", "B", (8, 15)),
        ("北碧", "B", (8, 20)),
        ("叻丕", "B", (5, 15)),
        ("佛统", "B", (4, 10)),
        ("沙没颂堪", "B", (3, 8)),
        ("沙没沙空", "B", (2, 6)),
        ("沙没巴干", "B", (2, 5)),
        ("暖武里", "B", (1, 3)),
        ("巴吞他尼", "B", (1, 2)),
        ("横滨", "B", (150, 300)),
        ("神户", "B", (100, 200)),
        ("广岛", "B", (80, 150)),
        ("仙台", "B", (60, 120)),
        ("福岛", "B", (40, 80)),
        ("新潟", "B", (30, 60)),
        ("富山", "B", (25, 50)),
        ("金泽", "B", (20, 40)),
        ("长野", "B", (20, 40)),
        ("山梨", "B", (15, 30)),
        ("静冈", "B", (30, 60)),
        ("爱知", "B", (150, 300)),
        ("三重", "B", (20, 40)),
        ("滋贺", "B", (15, 30)),
        ("兵库", "B", (100, 200)),
        ("奈良", "B", (15, 30)),
        ("和歌山", "B", (10, 25)),
        ("鸟取", "B", (8, 15)),
        ("岛根", "B", (5, 15)),
        ("冈山", "B", (30, 60)),
        ("山口", "B", (15, 30)),
        ("德岛", "B", (8, 20)),
        ("香川", "B", (10, 25)),
        ("爱媛", "B", (12, 25)),
        ("高知", "B", (8, 15)),
        ("佐贺", "B", (5, 15)),
        ("长崎", "B", (15, 30)),
        ("熊本", "B", (15, 30)),
        ("大分", "B", (10, 25)),
        ("宫崎", "B", (8, 20)),
        ("鹿儿岛", "B", (12, 25)),
        ("冲绳", "B", (80, 150)),
        ("富国岛", "B", (60, 120)),
        ("岘港", "B", (80, 150)),
        ("会安", "B", (30, 60)),
        ("顺化", "B", (20, 40)),
        ("芽庄", "B", (40, 80)),
        ("大叻", "B", (15, 30)),
        ("美奈", "B", (15, 30)),
        ("头顿", "B", (10, 25)),
        ("芹苴", "B", (8, 15)),
        ("金边", "B", (80, 150)),
        ("暹粒", "B", (60, 120)),
        ("西哈努克", "B", (30, 60)),
        ("马德望", "B", (15, 30)),
        ("磅湛", "B", (10, 25)),
        ("磅同", "B", (8, 20)),
        ("桔井", "B", (5, 15)),
        ("上丁", "B", (4, 10)),
        ("拉达那基里", "B", (3, 8)),
        ("蒙多基里", "B", (2, 6)),
        ("柏威夏", "B", (2, 5)),
        ("奥多棉吉", "B", (1, 3)),
        ("班迭棉吉", "B", (1, 2)),
        ("菩萨", "B", (1, 2)),
        ("贡布", "B", (1, 2)),
        ("茶胶", "B", (1, 2)),
        ("柴桢", "B", (1, 2)),
        ("波罗勉", "B", (1, 2)),
        ("干丹", "B", (1, 2)),
        ("磅士卑", "B", (1, 2)),
        ("磅清扬", "B", (1, 2)),
        
        # C类城市测试
        ("轻井泽", "C", (30, 80)),
        ("箱根", "C", (20, 60)),
        ("热海", "C", (15, 40)),
        ("伊豆", "C", (10, 30)),
        ("河口湖", "C", (10, 30)),
        ("白川乡", "C", (5, 15)),
        ("高山", "C", (8, 20)),
        ("松本", "C", (8, 20)),
        ("上高地", "C", (3, 10)),
        ("立山黑部", "C", (5, 15)),
        ("白滨", "C", (8, 20)),
        ("那智胜浦", "C", (5, 15)),
        ("熊野", "C", (5, 15)),
        ("出云", "C", (3, 10)),
        ("松江", "C", (3, 10)),
        ("米子", "C", (2, 8)),
        ("境港", "C", (1, 5)),
        ("仓吉", "C", (1, 5)),
        ("三朝", "C", (1, 3)),
        ("三德山", "C", (1, 3)),
        ("大山", "C", (1, 5)),
        ("皆生", "C", (1, 3)),
        ("汤原", "C", (1, 3)),
        ("奥大山", "C", (1, 3)),
        ("蒜山", "C", (1, 3)),
        ("津山", "C", (1, 5)),
        ("美作", "C", (1, 3)),
        ("胜山", "C", (1, 3)),
        ("汤田", "C", (1, 3)),
        ("萩", "C", (1, 5)),
        ("长门", "C", (1, 5)),
        ("下关", "C", (3, 10)),
        ("岩国", "C", (1, 5)),
        ("柳井", "C", (1, 3)),
        ("周南", "C", (1, 5)),
        ("光", "C", (1, 3)),
        ("防府", "C", (1, 3)),
        ("宇部", "C", (1, 5)),
        ("山阳小野田", "C", (1, 3)),
        ("美祢", "C", (1, 3)),
        ("阿武", "C", (1, 3)),
        ("美东", "C", (1, 3)),
        ("阿东", "C", (1, 3)),
        ("田布施", "C", (1, 3)),
        ("平生", "C", (1, 3)),
        ("上关", "C", (1, 3)),
        ("和木", "C", (1, 3)),
        ("玖珂", "C", (1, 3)),
        ("锦", "C", (1, 3)),
        ("美川", "C", (1, 3)),
        ("由宇", "C", (1, 3)),
        ("大竹", "C", (1, 3)),
        ("大野", "C", (1, 3)),
        ("廿日市", "C", (1, 3)),
        ("安芸高田", "C", (1, 3)),
        ("江田岛", "C", (1, 3)),
        ("安芸太田", "C", (1, 3)),
        ("熊野町", "C", (1, 3)),
        ("坂町", "C", (1, 3)),
        ("府中町", "C", (1, 3)),
        ("海田町", "C", (1, 3)),
        ("大崎上岛", "C", (1, 3)),
        ("大崎下岛", "C", (1, 3)),
        ("蒲刈", "C", (1, 3)),
        ("安芸津", "C", (1, 3)),
        ("丰町", "C", (1, 3)),
        ("濑户田", "C", (1, 3)),
        ("生口岛", "C", (1, 3)),
        ("因岛", "C", (1, 3)),
        ("尾道", "C", (1, 5)),
        ("福山", "C", (3, 10)),
        ("府中", "C", (1, 5)),
        ("神石", "C", (1, 3)),
        ("世罗", "C", (1, 3)),
        ("三原", "C", (1, 5)),
        ("竹原", "C", (1, 3)),
        ("东广岛", "C", (1, 3)),
        
        # 未知城市测试
        ("未知城市", "C", (0, 0)),
        ("测试城市", "C", (0, 0)),
        ("小城市", "C", (0, 0)),
    ]
    
    print("Testing Enhanced City Classification System:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for city_name, expected_tier, expected_range in test_cases:
        tier, city_info = city_classifier.classify_city(city_name)
        hotel_count = city_info.get('hotel_count', 0)
        is_fallback = city_info.get('is_fallback', False)
        
        # Check tier
        tier_correct = tier == expected_tier
        
        # Check hotel count range (for known cities)
        count_correct = True
        if not is_fallback and expected_range != (0, 0):
            min_count, max_count = expected_range
            count_correct = min_count <= hotel_count <= max_count
        
        status = "✅ PASS" if (tier_correct and count_correct) else "❌ FAIL"
        
        print(f"{status} {city_name:15} -> {tier} (expected: {expected_tier}) | Hotels: {hotel_count} | Fallback: {is_fallback}")
        
        if tier_correct and count_correct:
            passed += 1
        else:
            failed += 1
            if not tier_correct:
                print(f"    ❌ Tier mismatch: got {tier}, expected {expected_tier}")
            if not count_correct and not is_fallback:
                min_count, max_count = expected_range
                print(f"    ❌ Hotel count out of range: got {hotel_count}, expected {min_count}-{max_count}")
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0

def test_preference_collection():
    """Test preference collection logic"""
    
    # Test cases: (city_name, user_message, should_collect)
    test_cases = [
        # A类城市 - 需要收集偏好
        ("上海", "推荐一些酒店", True),
        ("东京", "有什么好的酒店吗", True),
        ("曼谷", "帮我找酒店", True),
        
        # A类城市 - 已经提供偏好，不需要收集
        ("上海", "推荐一些预算1000-2000的5星酒店", False),
        ("东京", "我要万豪品牌的酒店", False),
        ("曼谷", "市中心附近的奢华酒店", False),
        
        # B类城市 - 需要收集偏好
        ("清迈", "推荐酒店", True),
        ("名古屋", "有什么酒店", True),
        ("大阪", "帮我找住宿", True),
        
        # B类城市 - 已经提供偏好，不需要收集
        ("清迈", "推荐一些预算500-1000的酒店", False),
        ("名古屋", "市中心附近的4星酒店", False),
        ("大阪", "交通便利的酒店", False),
        
        # C类城市 - 不需要收集偏好
        ("轻井泽", "推荐酒店", False),
        ("箱根", "有什么酒店", False),
        ("未知城市", "推荐酒店", False),
    ]
    
    print("\nTesting Preference Collection Logic:")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for city_name, user_message, expected in test_cases:
        result = city_classifier.should_collect_preferences(city_name, user_message)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status} {city_name:10} | {user_message:30} -> {result} (expected: {expected})")
        
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0

def test_preference_prompts():
    """Test preference collection prompts"""
    
    print("\nTesting Preference Collection Prompts:")
    print("=" * 50)
    
    # Test A类城市提示
    a_prompt = city_classifier.build_preference_prompt("上海")
    print("A类城市提示 (上海):")
    print(a_prompt)
    print()
    
    # Test B类城市提示
    b_prompt = city_classifier.build_preference_prompt("清迈")
    print("B类城市提示 (清迈):")
    print(b_prompt)
    print()
    
    # Test C类城市提示
    c_prompt = city_classifier.build_preference_prompt("轻井泽")
    print("C类城市提示 (轻井泽):")
    print(c_prompt)
    print()

def test_city_statistics():
    """Test city statistics"""
    
    print("\nTesting City Statistics:")
    print("=" * 30)
    
    stats = city_classifier.get_city_statistics()
    print(f"A类城市数量: {stats['A_class_count']}")
    print(f"B类城市数量: {stats['B_class_count']}")
    print(f"C类城市数量: {stats['C_class_count']}")
    print(f"总城市数量: {stats['total_cities']}")
    
    return True

if __name__ == "__main__":
    print("Testing Enhanced City Classification System with Hotel Data Mapping")
    print("=" * 70)
    
    # Run tests
    test1_passed = test_city_classification()
    test2_passed = test_preference_collection()
    test_preference_prompts()
    test_city_statistics()
    
    print("\nOverall Results:")
    print("=" * 30)
    print(f"City Classification: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Preference Collection: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print(f"Overall: {'✅ ALL TESTS PASSED' if test1_passed and test2_passed else '❌ SOME TESTS FAILED'}")
