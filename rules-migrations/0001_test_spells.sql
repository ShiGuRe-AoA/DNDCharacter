CREATE TABLE spells (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  english_name TEXT NOT NULL,
  name_key TEXT NOT NULL,
  english_key TEXT NOT NULL,
  ruleset TEXT NOT NULL,
  source TEXT NOT NULL,
  source_type TEXT NOT NULL,
  level INTEGER NOT NULL CHECK (level BETWEEN 0 AND 9),
  school TEXT NOT NULL,
  verbal INTEGER NOT NULL CHECK (verbal IN (0, 1)),
  somatic INTEGER NOT NULL CHECK (somatic IN (0, 1)),
  material INTEGER NOT NULL CHECK (material IN (0, 1)),
  concentration INTEGER NOT NULL CHECK (concentration IN (0, 1)),
  ritual INTEGER NOT NULL CHECK (ritual IN (0, 1)),
  duration TEXT NOT NULL,
  description TEXT NOT NULL
);

-- Test records from the supplied catalog. Descriptions are short summaries.
INSERT INTO spells (
  id, name, english_name, name_key, english_key, ruleset, source, source_type,
  level, school, verbal, somatic, material, concentration, ritual, duration, description
) VALUES
  ('spell-2014-light', '光亮术', 'Light', '光亮术', 'light', '2014', '玩家手册', 'core', 0, 'evocation', 1, 0, 1, 0, 0, '1小时', '使一个物体发光，照亮周围区域。'),
  ('spell-2014-mage-hand', '法师之手', 'Mage Hand', '法师之手', 'magehand', '2014', '玩家手册', 'core', 0, 'conjuration', 1, 1, 0, 0, 0, '1 分钟', '创造一只可操控的幽灵手，用于移动物品或执行简单操作。'),
  ('spell-2014-guidance', '神导术', 'Guidance', '神导术', 'guidance', '2014', '玩家手册', 'core', 0, 'divination', 1, 1, 0, 1, 0, '专注，至多 1 分钟', '在持续时间内，为目标指定的属性检定提供额外骰子。'),
  ('spell-2014-detect-magic', '侦测魔法', 'Detect Magic', '侦测魔法', 'detectmagic', '2014', '玩家手册', 'core', 1, 'divination', 1, 1, 0, 1, 1, '专注，至多 10 分钟', '感知附近的魔法，并可进一步辨认可见魔法的灵光。'),
  ('spell-2014-shield', '护盾术', 'Shield', '护盾术', 'shield', '2014', '玩家手册', 'core', 1, 'abjuration', 1, 1, 0, 0, 0, '1 轮', '短暂提高护甲等级，并防护魔法飞弹。'),
  ('spell-2014-cure-wounds', '疗伤术', 'Cure Wounds', '疗伤术', 'curewounds', '2014', '玩家手册', 'core', 1, 'evocation', 1, 1, 0, 0, 0, '立即', '接触目标并为其恢复生命值。'),
  ('spell-2014-bless', '祝福术', 'Bless', '祝福术', 'bless', '2014', '玩家手册', 'core', 1, 'enchantment', 1, 1, 1, 1, 0, '专注，至多 1 分钟', '在持续时间内，为受祝福目标的攻击检定和豁免检定提供额外骰子。'),
  ('spell-2014-magic-missile', '魔法飞弹', 'Magic Missile', '魔法飞弹', 'magicmissile', '2014', '玩家手册', 'core', 1, 'evocation', 1, 1, 0, 0, 0, '立即', '发射多枚必定命中的力场飞弹，可以集中或分散攻击。'),
  ('spell-2014-misty-step', '迷踪步', 'Misty Step', '迷踪步', 'mistystep', '2014', '玩家手册', 'core', 2, 'conjuration', 1, 0, 0, 0, 0, '立即', '短距离传送到一个能看见的未被占据空间。'),
  ('spell-2014-invisibility', '隐形术', 'Invisibility', '隐形术', 'invisibility', '2014', '玩家手册', 'core', 2, 'illusion', 1, 1, 1, 1, 0, '专注，至多 1 小时', '使目标隐形，直到持续时间结束或触发提前结束的条件。'),
  ('spell-2014-counterspell', '法术反制', 'Counterspell', '法术反制', 'counterspell', '2014', '玩家手册', 'core', 3, 'abjuration', 0, 1, 0, 0, 0, '立即', '尝试打断附近生物正在施展的法术。'),
  ('spell-2014-fireball', '火球术', 'Fireball', '火球术', 'fireball', '2014', '玩家手册', 'core', 3, 'evocation', 1, 1, 1, 0, 0, '立即', '在指定位置引发爆炸，对范围内的生物造成火焰伤害。'),
  ('spell-2024-light', '光亮术', 'Light', '光亮术', 'light', '2024', '玩家手册2024', 'core', 0, 'evocation', 1, 0, 1, 0, 0, '1小时', '使一个物体发光，照亮周围区域。'),
  ('spell-2024-mage-hand', '法师之手', 'Mage Hand', '法师之手', 'magehand', '2024', '玩家手册2024', 'core', 0, 'conjuration', 1, 1, 0, 0, 0, '1分钟', '创造一只可操控的幽灵手，用于移动物品或执行简单操作。'),
  ('spell-2024-guidance', '神导术', 'Guidance', '神导术', 'guidance', '2024', '玩家手册2024', 'core', 0, 'divination', 1, 1, 0, 1, 0, '专注，至多1分钟', '在持续时间内，为目标指定的属性检定提供额外骰子。'),
  ('spell-2024-detect-magic', '侦测魔法', 'Detect Magic', '侦测魔法', 'detectmagic', '2024', '玩家手册2024', 'core', 1, 'divination', 1, 1, 0, 1, 1, '专注，至多10分钟', '感知附近的魔法，并可进一步辨认可见魔法的灵光。'),
  ('spell-2024-shield', '护盾术', 'Shield', '护盾术', 'shield', '2024', '玩家手册2024', 'core', 1, 'abjuration', 1, 1, 0, 0, 0, '1 轮', '短暂提高护甲等级，并防护魔法飞弹。'),
  ('spell-2024-cure-wounds', '疗伤术', 'Cure Wounds', '疗伤术', 'curewounds', '2024', '玩家手册2024', 'core', 1, 'abjuration', 1, 1, 0, 0, 0, '立即', '接触目标并为其恢复生命值。'),
  ('spell-2024-bless', '祝福术', 'Bless', '祝福术', 'bless', '2024', '玩家手册2024', 'core', 1, 'enchantment', 1, 1, 1, 1, 0, '专注，至多1分钟', '在持续时间内，为受祝福目标的攻击检定和豁免检定提供额外骰子。'),
  ('spell-2024-magic-missile', '魔法飞弹', 'Magic Missile', '魔法飞弹', 'magicmissile', '2024', '玩家手册2024', 'core', 1, 'evocation', 1, 1, 0, 0, 0, '立即', '发射多枚必定命中的力场飞弹，可以集中或分散攻击。'),
  ('spell-2024-misty-step', '迷踪步', 'Misty Step', '迷踪步', 'mistystep', '2024', '玩家手册2024', 'core', 2, 'conjuration', 1, 0, 0, 0, 0, '立即', '短距离传送到一个能看见的未被占据空间。'),
  ('spell-2024-invisibility', '隐形术', 'Invisibility', '隐形术', 'invisibility', '2024', '玩家手册2024', 'core', 2, 'illusion', 1, 1, 1, 1, 0, '专注，至多1小时', '使目标隐形，直到持续时间结束或触发提前结束的条件。'),
  ('spell-2024-counterspell', '法术反制', 'Counterspell', '法术反制', 'counterspell', '2024', '玩家手册2024', 'core', 3, 'abjuration', 0, 1, 0, 0, 0, '立即', '尝试打断附近生物正在施展的法术。'),
  ('spell-2024-fireball', '火球术', 'Fireball', '火球术', 'fireball', '2024', '玩家手册2024', 'core', 3, 'evocation', 1, 1, 1, 0, 0, '立即', '在指定位置引发爆炸，对范围内的生物造成火焰伤害。');
