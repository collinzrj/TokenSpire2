using System.Collections.Generic;

namespace TokenSpire2.Llm;

public enum PromptLang { En, Zh }

public static class PromptStrings
{
    public static PromptLang Language { get; set; } = PromptLang.Zh;

    public static string Get(string key) =>
        _strings.TryGetValue(key, out var pair)
            ? (Language == PromptLang.Zh ? pair.Zh : pair.En)
            : $"[MISSING:{key}]";

    public static string Get(string key, params object[] args) =>
        string.Format(Get(key), args);

    private static readonly Dictionary<string, (string En, string Zh)> _strings = new()
    {
        // ========== System Prompt ==========
        ["SystemPrompt"] = (
@"You are an expert Slay the Spire 2 player making decisions in a live game. You will receive game state descriptions and must respond with your decision.

RESPONSE FORMAT — follow these EXACTLY:

For COMBAT turns:
- List cards to play, one per line: PLAY <card_index> or PLAY <card_index> -> <enemy_index>
- Card indices are numbers [1], [2], etc. Enemy indices are letters [A], [B], etc.
- To use a potion: POTION <P_index> or POTION <P_index> -> <enemy_letter> (potions are free, no energy cost)
- If you want to end your turn after playing, add END_TURN on its own line
- If a card draws more cards, OMIT END_TURN — you will be shown the updated hand and can continue playing
- Example (use a potion then play cards):
  POTION P1 -> A
  PLAY 3 -> A
  PLAY 2
  PLAY 1 -> A
  END_TURN
- Example (play a draw card, then wait to see new cards):
  PLAY 2
  PLAY 1 -> A

For CHOICE decisions (events, map, rest site, relics, card grid, etc.):
- Reply with just the number on the first line: CHOOSE <number>
- Example: CHOOSE 2

For REWARDS (after combat):
- TAKE <number> to claim a reward (gold, potion, etc.)
- CARD <number> to pick a specific card from the card reward (or omit to skip cards)
- End with DONE
- Example:
  TAKE 1
  TAKE 2
  CARD 2
  DONE

For SHOP decisions:
- List items to buy, one per line: BUY <number>
- End with LEAVE on its own line
- Example:
  BUY 3
  BUY 7
  LEAVE

STRATEGY GUIDELINES:
- In combat, try to block ALL incoming damage — survival is the top priority
- AVOID all elite fights regardless of HP level
- Prefer unknown rooms (?) for more events and resources
- Build deck synergy — don't add cards that don't fit your archetype
- Manage energy efficiently — play high-impact cards first
- Remove weak cards (Strikes) from your deck when possible

CONTINUAL LEARNING:
You are in a continual learning loop. After each run you will write new lessons that get APPENDED to your accumulated memory. Memory persists across runs — do not repeat existing content, only write new discoveries.

Output ONLY action commands. Do not add any reasoning or explanation.",

@"你是一位杰出的《杀戮尖塔2》玩家，正在实时游戏中做决策。你会收到游戏状态描述，必须回复你的决定。

回复格式 — 严格遵守：

战斗回合：
- 每行打出一张牌：PLAY <卡牌序号> 或 PLAY <卡牌序号> -> <敌人字母>
- 卡牌序号为数字 [1], [2] 等，敌人序号为字母 [A], [B] 等
- 使用药水：POTION <P序号> 或 POTION <P序号> -> <敌人字母>（药水免费，不消耗能量）
- 打完牌后结束回合，单独写一行 END_TURN
- 如果某张牌会抽牌，不要写 END_TURN —— 系统会展示更新后的手牌让你继续出牌
- 示例（先用药水再出牌）：
  POTION P1 -> A
  PLAY 3 -> A
  PLAY 2
  PLAY 1 -> A
  END_TURN
- 示例（打出抽牌卡，等待新手牌）：
  PLAY 2
  PLAY 1 -> A

选择类决策（事件、地图、休息点、遗物、卡牌选择等）：
- 第一行回复数字：CHOOSE <编号>
- 示例：CHOOSE 2

战斗奖励：
- TAKE <编号> 领取奖励（金币、药水等）
- CARD <编号> 选择一张卡牌奖励（不选则跳过）
- 最后写 DONE
- 示例：
  TAKE 1
  TAKE 2
  CARD 2
  DONE

商店决策：
- 每行购买一件物品：BUY <编号>
- 最后单独写 LEAVE
- 示例：
  BUY 3
  BUY 7
  LEAVE

策略指南：
- 战斗中尽量格挡掉所有伤害，生存优先
- 不管血量多少都尽量避开所有精英
- 多去未知房间（？）获取更多事件和资源
- 构建牌组联动 —— 不要加入与你流派不搭的牌
- 高效管理能量 —— 优先打高价值牌
- 有机会时移除弱牌（打击）

持续学习模式：
你处于持续学习循环中。每局结束后，你将写下本局的新教训，追加到已有记忆中。记忆在多局间持续积累——不要重复已有内容，只写新发现。

只输出操作指令，不要附加任何推理或解释。"
        ),

        // ========== Game Over ==========
        // {0} = run stats, {1} = current memory (or "empty")
        ["GameOverReflection"] = (
@"=== GAME OVER ===
This run has ended. Here are the stats:
{0}
Your accumulated memory from previous runs:
---
{1}
---

Write ONLY the NEW lessons from THIS run. Do NOT repeat anything already in the memory above. Summarize the run stats in one line, then list new insights. Your output will be APPENDED to the existing memory. Keep it concise — you have a 4096 token budget for this update.",

@"=== 游戏结束 ===
本局游戏已结束。以下是本局统计：
{0}
你之前积累的记忆：
---
{1}
---

只写本局的新教训。不要重复已有记忆中的内容。先用一行总结本局数据，然后列出新发现。你的输出会被追加到已有记忆后面。保持简洁——本次更新限4096 token。"
        ),

        // ========== Combat ==========
        ["CombatUnavailable"] = (
            "Combat state unavailable.",
            "战斗状态不可用。"
        ),
        ["CombatHeader"] = (
            "=== COMBAT — YOUR TURN ===",
            "=== 战斗 — 你的回合 ==="
        ),
        ["HpBlockEnergy"] = (
            "HP: {0}/{1} | Block: {2} | Energy: {3}/{4}",
            "生命值: {0}/{1} | 格挡: {2} | 能量: {3}/{4}"
        ),
        ["YourRelics"] = (
            "Relics: {0}",
            "遗物: {0}"
        ),
        ["YourPowers"] = (
            "Your powers: {0}",
            "你的能力: {0}"
        ),
        ["Hand"] = (
            "Hand:",
            "手牌："
        ),
        ["TargetSingleEnemy"] = (
            " [Target: Single Enemy]",
            " [目标: 单体敌人]"
        ),
        ["Unplayable"] = (
            " (UNPLAYABLE)",
            " (无法打出)"
        ),
        ["Energy"] = (
            "energy",
            "能量"
        ),
        ["DrawDiscardPile"] = (
            "Draw pile: {0} | Discard pile: {1}",
            "抽牌堆: {0} | 弃牌堆: {1}"
        ),
        ["Potions"] = (
            "Potions:",
            "药水："
        ),
        ["Enemies"] = (
            "Enemies:",
            "敌人："
        ),
        ["Unknown"] = (
            "Unknown",
            "未知"
        ),
        ["Intent"] = (
            "Intent: {0}",
            "意图: {0}"
        ),
        ["Attack"] = (
            "Attack {0}",
            "攻击 {0}"
        ),
        ["AttackUnknown"] = (
            "Attack ?",
            "攻击 ?"
        ),
        ["Powers"] = (
            "Powers: {0}",
            "能力: {0}"
        ),
        ["CombatInstruction"] = (
            "Which cards/potions do you play this turn? Use PLAY <index> [-> <enemy_letter>] or POTION <P_index> [-> <enemy_letter>], then END_TURN.",
            "这回合打哪些牌/用哪些药水？使用 PLAY <序号> [-> <敌人字母>] 或 POTION <P序号> [-> <敌人字母>]，然后 END_TURN。"
        ),

        // ========== Card Reward ==========
        ["CardRewardHeader"] = (
            "=== CARD REWARD ===",
            "=== 卡牌奖励 ==="
        ),
        ["ChooseCardForDeck"] = (
            "Choose a card to add to your deck:",
            "选择一张牌加入你的牌组："
        ),
        ["UnknownCard"] = (
            "(unknown card)",
            "(未知卡牌)"
        ),
        ["SkipCard"] = (
            "Skip (don't add any card)",
            "跳过（不添加卡牌）"
        ),
        ["ReplyChoose"] = (
            "Reply with CHOOSE <number>.",
            "请回复 CHOOSE <编号>。"
        ),

        // ========== Rewards ==========
        ["RewardsHeader"] = (
            "=== REWARDS ===",
            "=== 奖励 ==="
        ),
        ["RewardsIntro"] = (
            "You may TAKE multiple rewards. Available:",
            "你可以领取多个奖励，可选项："
        ),
        ["GoldReward"] = (
            "Gold ({0}g)",
            "金币 ({0}g)"
        ),
        ["CardRewardDesc"] = (
            "Card Reward (pick one below, or skip)",
            "卡牌奖励（从下方选择一张，或跳过）"
        ),
        ["PotionReward"] = (
            "Potion: {0}",
            "药水: {0}"
        ),
        ["CardChoicesFor"] = (
            "Card choices for reward {0} (pick ONE card, or SKIP):",
            "奖励 {0} 的卡牌选项（选一张，或跳过）："
        ),
        ["RewardsInstruction"] = (
            "Reply with TAKE commands, then DONE:",
            "请用 TAKE 命令领取，最后写 DONE："
        ),
        ["TakeInstruction"] = (
            "  TAKE <number> — take a reward (gold, potion, etc.)",
            "  TAKE <编号> — 领取奖励（金币、药水等）"
        ),
        ["CardInstruction"] = (
            "  CARD <number> — pick a card from the card reward (or omit to skip cards)",
            "  CARD <编号> — 选择一张卡牌奖励（不选则跳过）"
        ),
        ["DoneInstruction"] = (
            "  DONE — proceed to next room",
            "  DONE — 前往下一个房间"
        ),
        ["RewardsExample"] = (
            "Example: TAKE 1 / CARD 2 / DONE",
            "示例: TAKE 1 / CARD 2 / DONE"
        ),

        // ========== Map ==========
        ["MapHeader"] = (
            "=== MAP — CHOOSE NEXT ROOM ===",
            "=== 地图 — 选择下一个房间 ==="
        ),
        ["CurrentPosition"] = (
            "Current position: row {0}, col {1}",
            "当前位置: 第{0}行, 第{1}列"
        ),
        ["CurrentPositionStart"] = (
            "Current position: start (not yet on map)",
            "当前位置: 起点（尚未进入地图）"
        ),
        ["HpGold"] = (
            "HP: {0}/{1} | Gold: {2}",
            "生命值: {0}/{1} | 金币: {2}"
        ),
        ["FullMap"] = (
            "Full map (row 1 = first rooms, higher rows = closer to boss):",
            "完整地图（第1行=起始房间，行数越大越接近Boss）："
        ),
        ["AvailableNextRooms"] = (
            "Available next rooms:",
            "可选的下一个房间："
        ),

        // ========== Event ==========
        ["EventHeader"] = (
            "=== EVENT ===",
            "=== 事件 ==="
        ),
        ["EventNoOptions"] = (
            "(No options available yet — dialogue in progress)",
            "（暂无可选项 —— 对话进行中）"
        ),
        ["ChooseOption"] = (
            "Choose an option:",
            "选择一个选项："
        ),
        ["ProceedLeave"] = (
            "(Proceed/Leave)",
            "（继续/离开）"
        ),
        ["Option"] = (
            "Option",
            "选项"
        ),

        // ========== Rest Site ==========
        ["RestSiteHeader"] = (
            "=== REST SITE ===",
            "=== 休息点 ==="
        ),
        ["AvailableOptions"] = (
            "Available options:",
            "可选操作："
        ),

        // ========== Shop ==========
        ["ShopHeader"] = (
            "=== SHOP ===",
            "=== 商店 ==="
        ),
        ["GoldHp"] = (
            "Gold: {0} | HP: {1}/{2}",
            "金币: {0} | 生命值: {1}/{2}"
        ),
        ["ShopUnavailable"] = (
            "(Shop inventory not available)",
            "（商店库存不可用）"
        ),
        ["Cards"] = (
            "Cards:",
            "卡牌："
        ),
        ["Relics"] = (
            "Relics:",
            "遗物："
        ),
        ["Sale"] = (
            " [SALE]",
            " [折扣]"
        ),
        ["NotEnoughGold"] = (
            " (NOT ENOUGH GOLD)",
            " (金币不足)"
        ),
        ["RemoveCard"] = (
            "Remove a card",
            "移除一张牌"
        ),
        ["Cost"] = (
            "Cost: {0}g",
            "价格: {0}g"
        ),
        ["LeaveShop"] = (
            "Leave shop (buy nothing more)",
            "离开商店（不再购买）"
        ),
        ["ShopInstruction"] = (
            "You may BUY multiple items. Reply with BUY <number> for each item, then LEAVE on its own line.",
            "你可以购买多件物品。每件写 BUY <编号>，最后单独写 LEAVE。"
        ),

        // ========== Card Grid ==========
        ["ChooseCardFromDeck"] = (
            "Choose a card from your deck:",
            "从你的牌组中选择一张牌："
        ),

        // ========== Generic Choice ==========
        ["GenericChoice"] = (
            "Choose from {0} options (1-{1}).",
            "从 {0} 个选项中选择 (1-{1})。"
        ),

        // ========== Card Selector (mid-combat) ==========
        ["SelectCards"] = (
            "=== SELECT {0} CARD(S) ===",
            "=== 选择 {0} 张牌 ==="
        ),
        ["SelectCardsIntro"] = (
            "Choose {0} card(s) from the following (mid-combat effect, e.g. Armaments upgrade, Headbutt pick, etc.):",
            "从以下卡牌中选择 {0} 张（战斗中效果，例如军备升级、头锤选择等）："
        ),
        ["SelectCardsNonCombat"] = (
            "Choose {0} card(s) to REMOVE from your deck (e.g. from a relic or event effect):",
            "从你的牌组中选择 {0} 张牌移除（例如遗物或事件效果）："
        ),
        ["ReplyChooseCount"] = (
            "Reply with CHOOSE <number> (pick {0}).",
            "请回复 CHOOSE <编号>（选 {0} 张）。"
        ),
    };
}
