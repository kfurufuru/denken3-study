# Claude Code の競合AI 調査メモ（2026年9月時点）

調査日: 2026-09-23 / 方法: Web検索（一次情報への直接アクセスは一部ネットワーク制限で不可。検索結果の要約に依拠）

> **信頼度の注意**: 市場シェアやベンチマーク数値は、出典によって定義・母集団がバラバラで、ベンダー自己申告も多い。
> 下の数字は「傾向を掴むための目安」であり、単独の数値を根拠に判断しないこと。

---

## 1. 結論（3行）

1. **米国勢は「モデル＋エージェント製品」の総力戦**。OpenAI（Codex / GPT-6）、Google（Antigravity）、Cursor、GitHub Copilot が Claude Code と正面から競合。
2. **中国勢は「オープンウェイト×低価格」で急接近**。Kimi K3・DeepSeek V4・Qwen3.8 は最前線の米国モデルに「少し後ろ」まで迫り、しかも自前サーバーで動かせる。
3. **ただし「飛躍的に伸びている」は半分正しく半分誇張**。性能差は縮小したが、ベンチマークの飽和・汚染問題があり、実務での差は数値ほど単純ではない。

---

## 2. 米国勢

| 製品 | 提供元 | 2026年の主な動き | Claude Code との関係 |
|---|---|---|---|
| **Codex (CLI/クラウド)** | OpenAI | 2026-09-22 に GPT-6 Sol / Luna を投入。API価格を GPT-5.6 比で約50%値下げ。Codex CLI は即日対応 | 最も直接的なライバル。利用率は1月3%→5〜7月16%と約5倍の急伸（JetBrains調査） |
| **Antigravity (CLI/デスクトップ)** | Google | 2026年5月、Gemini CLI（OSS）を閉源の Antigravity CLI に統合。個人向け Jules は6/18に終了 | エージェント統合型IDEで対抗。OSSからクローズドへ転換した点は開発者の反発も |
| **Cursor** | Anysphere | ARR は $3B（5月）→推計 $4B、評価額 $50〜60B 規模。自社モデル Composer で粗利改善 | 「編集はCursor、重いタスクはClaude Code」の併用が典型パターン |
| **GitHub Copilot** | Microsoft/GitHub | Copilot CLI が3月にGA。OpenAI/Anthropic/Google/xAI のモデルを選べるマルチモデル化。6月から従量課金（AI Credits）へ | ユーザー数最大級。Claudeモデルも中で使える「プラットフォーム」路線 |

**Claude Code 側の現状（比較用）**: 2026年5〜7月時点でプロ開発者の約39%が業務利用（1月は18%）、米国では47%。Claude Code 単体の収益ランレートは2026年2月時点で $2.5B 超。6月に Fable 5、9/1 に Fable 5.1 を投入。

### 市場シェアの数字が食い違う理由
- 「Copilot 42%」「Claude Code 28%」「Cursor 18%」など調査ごとに大きく違う。
- 原因: **ユーザー数・売上・満足度（NPS）・業務利用率** のどれを測っているかが違う。
- 共通して言えるのは「上位3〜4製品で市場の7割超」「70%のエンジニアが2〜4個のツールを併用」という点。**一強ではなく併用が常態**。

---

## 3. 中国勢

| モデル | 開発元 | 公開 | 特徴 |
|---|---|---|---|
| **Kimi K3** | Moonshot AI | 7月中旬発表、7/27 に重み公開 | 2.8兆パラメータ、100万トークン文脈。公開直後に Hugging Face トレンド1位。性能は Claude Fable 5 / GPT-5.6 Sol の「少し後ろ」と報道 |
| **DeepSeek V4 / V4-Pro** | DeepSeek | 2026-04-24 | 1.6兆パラメータMoE。**発表当日に Huawei Ascend 等の中国製チップへ対応**＝米国製GPUへの依存を下げる象徴 |
| **Qwen3.8-Max** | Alibaba | 8/3 発表、8/12 に重み公開 | 2.4兆パラメータ。16日間の自律コーディング（265コミット）を主張。**Claude Code や Codex からそのまま呼べる互換API** |
| **GLM-5.x** | Zhipu (Z.ai) | 継続更新 | 月$18〜の「Coding Plan」で Claude Code 等から使わせる戦略。ただし2月に30%以上値上げ |
| **MiniMax M3 など** | MiniMax 他 | — | 低価格サブスク競争（中国国内は月¥29〜） |

### 中国勢の戦略の本質
- **自前のCLIで勝負するより、モデルを安く出して Claude Code / Codex / Cline に「差し込ませる」**。Anthropic互換APIを提供しているのはその証拠。
- 米国の半導体輸出規制への対抗として、国産チップ（Ascend等）での動作を前面に出している。
- Stanford AI Index 2026 では、米中トップモデルの差は **Arenaスコアで2.7%**（2023年は17.5〜31.6ポイント差）。一方で**民間AI投資は米国が中国の約23倍**。「少ない投資で追いついた」効率の高さが注目点。

### 逆風（見落としやすい点）
- **蒸留疑惑**: Anthropic は Alibaba Qwen が約2万5千の不正アカウントで Claude を大量に問い合わせ（蒸留）したと主張。米政府も「蒸留キャンペーン」を規制理由に挙げている。
- **規制リスク**: 米連邦機関の多くが中国モデルを内部利用禁止。Kimi K3 公開後、トランプ政権が中国モデル禁止の動きを再燃と報道。民間企業への全面禁止は（現時点で）なし。
- **オープン路線の後退**: Alibaba・Zhipu がフラッグシップの一部をクローズド化し始めたとの報道も。「中国＝オープン」も固定ではない。

---

## 4. 「飛躍的に伸びている」をどう読むか（批判的視点）

1. **ベンチマークはもう当てにしにくい**
   SWE-bench Verified は上位が80〜95%で団子状態。OpenAI は汚染を理由に2026年2月に報告を停止。6月時点の某リーダーボードでは100件中99件がベンダー自己申告だった。
   → 「○○が95%！」という記事は割り引いて読む。より難しい **SWE-bench Pro**（上位でも50〜60%台）や実務での評価を見る。
2. **モデル性能 ≠ 製品の使いやすさ**
   コーディングエージェントの実力は「モデル × 足回り（ツール実行・文脈管理・権限・IDE連携）」の掛け算。中国モデルが強くても、それを動かす器として Claude Code 自体が使われている、という逆説がある。
3. **価格競争は本物**
   GPT-6 の50%値下げ、中国勢の月$20前後プラン。性能差が縮むほど、**価格・データの扱い・規制リスク**で選ばれる時代になる。

---

## 5. このリポジトリ（電験三種学習）への示唆

- 学習用途なら、**どのツールでも「解説の正確さ」を自分で検算する習慣**の方がツール選びより効く。AIは電気の計算で符号・単位・√3 を平気で間違える。
- 中国系モデルを安さで試すのは合理的だが、**個人の学習記録や弱点データを外部APIに送る点は意識**すること（どの国のサービスでも同じ）。
- 「話題のAIに乗り換える」判断は、**自分の具体タスク（例: 過去問の解説生成、弱点ランキング更新）で同じ問題を解かせて比較**してから。ニュースの数字だけで決めない。

---

## 出典（主なもの）

- [AI Coding Agents: Adoption Trends – JetBrains Blog](https://blog.jetbrains.com/research/2026/08/ai-coding-agent-adoption-2026/)
- [AI Coding Agent Market Share 2026 – andrew.ooo](https://andrew.ooo/answers/ai-coding-agent-market-share-cursor-claude-code-copilot-july-2026/)
- [AI Coding Tool Market Share Statistics 2026 – Presenc AI](https://presenc.ai/research/ai-coding-tool-market-share-statistics-2026)
- [OpenAI Launches GPT-6 Sol and Luna – gHacks](https://www.ghacks.net/2026/09/23/openai-launches-gpt-6-sol-and-luna-with-50-lower-api-pricing-than-gpt-5-6/)
- [openai/codex Releases – GitHub](https://github.com/openai/codex/releases)
- [Transitioning Gemini CLI to Antigravity CLI – Google Developers Blog](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/)
- [Bye-bye, Gemini CLI – The Register](https://www.theregister.com/ai-ml/2026/05/20/bye-bye-gemini-cli-google-nudges-devs-toward-antigravity/5243605)
- [Cursor in talks to raise $2B+ at $50B valuation – TechCrunch](https://techcrunch.com/2026/04/17/sources-cursor-in-talks-to-raise-2b-at-50b-valuation-as-enterprise-growth-surges/)
- [GitHub Copilot CLI Reaches GA – Visual Studio Magazine](https://visualstudiomagazine.com/articles/2026/03/02/github-copilot-cli-reaches-general-availability-bringing-agentic-coding-to-the-terminal.aspx)
- [Moonshot AI releases Kimi K3 open weights – Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/moonshot-ai-releases-weights-for-kimi-k3-firing-a-shot-across-the-bow-of-openai-and-anthropic-open-weight-model-performs-almost-as-well-as-frontier-models-while-being-2-3x-easier-to-run)
- [Kimi K3: The open-weights escalation – Interconnects](https://www.interconnects.ai/p/kimi-k3-the-open-weights-escalation)
- [Why DeepSeek's V4 matters – MIT Technology Review](https://www.technologyreview.com/2026/04/24/1136422/why-deepseeks-v4-matters/)
- [Huawei Ascend etc. Day 0 adaptation to DeepSeek-V4 – TrendForce](https://www.trendforce.com/news/2026/04/29/news-huawei-ascend-cambricon-and-hygon-completed-day-0-adaptation-to-deepseek-v4/)
- [Alibaba launches Qwen3.8 – TechNode](https://technode.com/2026/08/03/alibaba-launches-qwen3-8-with-2-4-trillion-parameters/)
- [Qwen3.8-Max claims 16-day autonomous coding run – Developer Tech](https://www.developer-tech.com/news/alibaba-qwen3-8-max-claims-16-day-autonomous-coding-run/)
- [Chinese AI Coding Plans – Standard Compute](https://standardcompute.com/chinese-ai-coding-plans)
- [The 2026 AI Index Report – Stanford HAI](https://hai.stanford.edu/ai-index/2026-ai-index-report)
- [Stanford AI Index: China nearly closed the gap – The Next Web](https://thenextweb.com/news/stanford-ai-index-2026-china-us-performance-gap)
- [Why U.S. tech and Washington are divided over Chinese AI models – Rest of World](https://restofworld.org/2026/silicon-valley-debate-chinese-open-weight-ai-models/)
- [Trump administration reviving push to ban Chinese AI models – Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/trump-administration-reportedly-reviving-push-to-ban-chinese-ai-models-following-kimi-k3-launch-citing-cybersecurity-concerns-downloadable-open-weights-could-make-an-outright-u-s-ban-nearly-impossible-to-enforce-amid-growing-adoption)
- [SWE-Bench Pro Leaderboard – Scale](https://labs.scale.com/leaderboard/swe_bench_pro)
- [SWE-bench Contamination & AI Coding Leaderboards – buildmvpfast](https://www.buildmvpfast.com/blog/benchmark-contamination-ai-coding-leaderboard-swe-bench-2026)
- [Introducing Claude Fable 5.1 – Anthropic](https://www.anthropic.com/claude-fable-and-mythos-5-1)
