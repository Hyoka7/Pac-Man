# Pac-Man

PythonとMLXで制作中のPac-Manです。外部パッケージで生成した迷路を使い、移動・敵・アイテム・画面遷移を段階的に実装しています。

## 起動

現在のプロジェクト設定はPython 3.14以上です。`uv` と、MLXを表示できるX11のグラフィカル環境が必要です。

```bash
uv sync
uv pip install ./src/mazegenerator-2.1.0-py3-none-any.whl ./src/mlx-2.2-py3-none-any.whl
.venv/bin/python pacman.py config.json
```

MLXと迷路生成パッケージは、現状では`pyproject.toml`の依存関係とは別に、同梱wheelからインストールします。

## 操作

| 画面 | キー | 動作 |
| --- | --- | --- |
| 共通 | Esc | 終了 |
| ホーム | ↑ / ↓ | メニューを選択（上下端で循環） |
| ホーム | Enter | 選択した項目を実行（Exitで終了） |
| ホーム | I | 操作説明 |
| ホーム | H | Top10ランキング |
| 操作説明 / ランキング | Enter | ホームへ戻る |
| ランキング | C | ランキング全件削除の確認画面を開く |
| 削除確認 | Y / N | 全件削除して保存 / キャンセル |
| プレイ中 | 矢印 / WASD | 移動、方向転換の予約 |
| プレイ中 | P | ポーズ |
| プレイ中 | C | 配色変更 |
| プレイ中 | `3111696` を順に入力 | チートの有効・無効を切り替え |
| プレイ中・チート有効 | N | 次レベルへ移動 |
| プレイ中・チート有効 | H | 壁貫通のON/OFF |
| プレイ中・チート有効 | X | 獲得スコア倍率を1倍 / 10倍に切り替え |
| プレイ中・チート有効 | F | 敵の移動を停止・再開 |
| ポーズ中 | P | 再開 |
| ポーズ中 | H | ホームへ戻る |
| ステージクリア | 任意キー（Esc以外） | 次レベルへ |
| ゲームオーバー / 全クリア | ASCII英数字・半角空白 | 名前を入力 |
| ゲームオーバー / 全クリア | Backspace | 名前の末尾を削除 |
| ゲームオーバー / 全クリア | Enter | 得点を保存してホームへ戻る |

ホームの項目はゲーム開始・操作説明・ランキング・終了の順です。初期選択はゲーム開始で、I/Hによる直接移動も使えます。ホームにはタイトル・メニュー・操作案内を表示し、ランキング専用画面に上位10件を1画面で表示します。Enterでホームへ戻ります。ランキングでCを押すと削除確認へ進み、Yで全件削除して保存、Nでキャンセルします。

チートコマンドはShiftを押さずに入力します。途中まで一致したキーは移動やレベル移動へ渡さず、不一致なら入力位置をリセットします。プレイ中・チート有効時は、Lで残機を1、Tで残り時間を10秒追加できます。チート解除時は敵の停止・壁貫通を解除し、スコア倍率を1倍へ戻します。停止中の敵にも接触判定はあります。

## 現在のゲーム動作

- レベル数と制限時間はConfigから取得します。同梱config.jsonは3レベルで、制限時間は90・120・180秒です。次レベルでは迷路を再生成します。
- プレイヤーは中央に最も近い通路から開始し、残機は3。次レベルへスコアと残機を引き継ぎます。
- 通常gum・スーパーgum・敵の得点はConfigから取得します。現在の既定値は10・50・200点です。四隅のスーパーgumで5秒間敵を食べられます。
- パワーアップ中は敵が青くなり、逃走Strategyで移動します。食べた敵は設定の得点を加算し、その敵の初期位置へ戻して5秒待機させます。待機中は描画・移動・接触判定を行わず、次レベルや死亡復帰などのリセットでは待機を解除します。
- ポーズ中は移動、レベルの残り時間、パワーアップの残り時間が止まります。
- 通常gumとスーパーgumをすべて食べるとステージクリア。最終レベルなら全クリアです。
- 時間切れはゲームオーバー。ただし同じフレームで最後のgumを食べた場合はクリアを優先します。
- HUDにレベル、得点、残機、制限時間を表示し、プレイ・ポーズ中のパワーアップ効果は下部の残り時間と中央へ縮むバーで示します。ホームや終了画面には効果表示を出しません。
- チート有効中はHUDに`CHEAT ON`を表示します。通常のHUDは`Lv`・`Score`・`Life`・`Time`の短い表記を使います。

設定ファイルを引数に1つ指定します。`python -m pacman config.json` または `make run`（既定はconfig.json）でも起動できます。別のファイルは `make run CONFIG=other.json` で指定します。

ParserはJSONを読み、行頭の空白を除いて `#` で始まるコメント行を無視します。文字列内の `#` は保持します。不足・不正な項目は警告をstderrへ出して、その項目だけ既定値へ戻します。未知のキーは無視し、ファイルが開けない・文字コードやJSON構文が不正・最上位がオブジェクトでない場合は、理由をstderrに表示して終了コード1で終了します。

| キー | 既定値・制限 |
| --- | --- |
| `highscore_filename` | `scores.json` |
| `lives` | 3、1以上 |
| `seed` | 42、1以上 |
| `points_per_pacgum` | 10、1以上 |
| `points_per_super_pacgum` | 50、1以上 |
| `points_per_ghost` | 200、1以上 |
| `levels` | 15×15・90秒の1ステージ。空や不正な配列も既定値へ戻す |
| 各レベルの `width` / `height` | 15、15〜30 |
| 各レベルの `max_time` | 90.0秒、90以上の有限値 |

ウィンドウは画面サイズから余裕を引いた固定サイズです。`_update_layout()`で迷路に収まるセルサイズと中央寄せの`offset_x`・`offset_y`を計算します。設定ごとの迷路サイズで生成し、レベル変更時には敵の初期位置・キャラクター半径・gumの行列数も更新します。同梱config.jsonのステージは15×15・25×15・25×25です。

ホーム・操作説明・ランキング・ポーズ・ステージクリア・ゲームオーバー・全クリアは、`needs_redraw`が立ったときだけループから描画します。状態変更、メニュー選択、名前入力でフラグを立て、描画後に下ろします。ウィンドウ再表示イベントからは直接再描画します。プレイ中のFPS制限はありません。

各画面の文字はPillowの標準フォントで描き、実際の文字幅と高さから中央位置を計算します。文字サイズはウィンドウ短辺の約1/30とし、行間・余白・枠線・HUD・バーの寸法を`GUI.update_layout()`でまとめて計算します。文字画像はフォント共通の高さと基準線を使い、小文字だけの名前でも縦位置が揃います。ランキングは順位・名前・得点を別々に配置し、名前の左端と得点の右端をそろえます。HUDは上部、パワーアップ表示は下部に配置します。迷路用の余白も、HUDと「残り時間の文字・文字とバーの間隔・バー・下端余白」の実寸から計算して、互いに重ならないよう確保します。

メニューなどの静止画面は濃紺の背景とパネル、水色の枠で統一しています。本文は白、タイトルとホームの選択項目は黄色です。ポーズは迷路を残した上にパネルを重ね、パワーアップバーも暗い土台と黄色の残量で表示します。

`pacman/visualize/image_renderer.py`の`ImageRenderer.draw_text(canvas, x, y, text, color, size)`で、Pillowの文字画像をCanvasへ合成します。共通の`ImageRenderer.draw_image(canvas, x, y, image)`が必要範囲の背景を取り出し、Pillowの`alpha_composite()`でまとめて合成して1行ずつ書き戻します。文字ごとのピクセルループを使わず、透明な背景と滑らかな縁を保ちます。画面外の部分は切り取ります。背景・ゲーム・文字をすべて描いた後、`mlx_put_image_to_window()`を1回だけ呼びます。`mlx_string_put()`、文字数のカウント、文字描画用の`mlx_sync()`は使いません。フォントと文字画像はクラス外の`@cache`関数で再利用し、クラス内のメソッドはそれを呼び出します。

BFSで追跡する敵は、事前計算した距離表から最短距離を1縮める方向を集め、同距離の候補からランダムに選びます。

現在はユーザーが実装した4種類の追跡を使います。赤はBFSStrategyで現在地、緑はAmbushStrategyで進行方向の最大3マス先、青はReverseAmbushStrategyで後方の最大3マス先、灰はBlockStrategyで通れる横道の隣接マスを狙います。灰は横道がなければ直接追跡します。各目標までの移動はBFS距離表を使い、壁やマップの端を越えて目標を予測しません。パワーアップ中はFleeBFSStrategyで逃走します。

GameからGhostとStrategyへプレイヤーの向きを渡します。現在は各敵が独立して目標を選んでおり、仲間との目標共有や担当調整は未実装です。以前AIが追加した協力追跡の試作は削除済みで、今後はユーザーが段階的に実装します。

敵も半径・色ごとの透明画像をキャッシュし、移動時には画像の貼り付け位置だけを変更します。逃走中の青色と復帰待ち中の非表示にも対応しています。プレイヤーも半径・方向・口の開き11段階ごとの画像を再利用します。

## ハイスコア

`HighscoreManager`は作成時にConfigの保存先（現在はカレントディレクトリの`scores.json`）を読み込みます。ファイルがなければ空で開始し、読み込み時と得点追加時に降順へ並べ替えます。追加時にはファイルへ保存します。

Pydanticの`ScoreEntry`（名前と得点）と`HighscoreData`を使います。

```json
{
  "scores": [
    {"name": "Alice", "score": 1200},
    {"name": "Bob", "score": 800}
  ]
}
```

現在同梱の`scores.json`は開発中のプレイ・テストデータです。Pydanticで名前1〜10文字（英数字と半角空白）・得点0以上を検証し、入力画面では空名を`kyonaha`として保存します。読み込み時の`ValidationError`・`OSError`・`ValueError`（不正UTF-8を含む）、保存時の`OSError`を捕捉して続行します。保存失敗時もメモリ上の得点は残ります。不正UTF-8のスコアファイルもエラーを表示して空のランキングで起動し、元ファイルは読み込み時に変更しません。安全なファイル置換は未実装です。

## 構成

| モジュール | 役割 |
| --- | --- |
| `pacman.py` | 設定ファイルを受け取る起動用入口 |
| `pacman/__main__.py` | 設定の読み込み、迷路生成と起動。`python -m pacman config.json` にも対応 |
| `pacman/parser/` | コメント付きJSONの読み込みと不正な項目の既定値への補正 |
| `pacman/models/` | 共通設定・レベル別設定のPydanticモデル |
| `pacman/game/game.py` | ゲーム進行、得点・衝突、復活、レベル準備 |
| `pacman/game/state.py` | Home・Ready・Playingなどの共通状態 |
| `pacman/game/player.py` / `pacman/game/ghost.py` | キャラクターの状態・役割と更新 |
| `pacman/game/maze.py` / `pacman/game/movement.py` | 壁、全通路のBFS距離表、移動・方向変更 |
| `pacman/game/directions.py` | 方向の順序、座標差、反対方向、壁ビットの共通定義 |
| `pacman/game/strategy.py` | 敵の目標選択と方向決定 |
| `pacman/game/pacgums.py` / `pacman/game/collision.py` | gumの配置・消費、接触判定 |
| `pacman/controls/game_input.py` | 状態別のキー処理、チート操作、名前入力 |
| `pacman/controls/keys.py` / `pacman/controls/cheating.py` | キー・方向の対応、ウィンドウへの要求、チートの順番入力 |
| `pacman/audio/manager.py` | BGMと効果音の再生 |
| `pacman/storage/highscore.py` | 得点モデルとJSONの保存・読み込み |
| `pacman/visualize/game_visualizer.py` | MLXの管理、描画、ゲーム更新と音声の呼び出し |
| `pacman/visualize/gui.py` | 各画面、ランキング、HUD、バー、パネル |
| `pacman/visualize/sprites.py` | Player・Ghostのキャッシュ付き画像生成 |
| `pacman/visualize/world_renderer.py` | 迷路・gum・Player・Ghostの描画 |
| `pacman/visualize/image_renderer.py` | 文字画像の生成・計測とRGBA画像の一括合成 |
| `pacman/visualize/canvas.py` | 画像バッファ、ピクセル描画、セルと画面座標の変換 |
| `pacman/visualize/mlx_events.py` | MLXフックで使うイベント番号・イベントマスク |

キー入力は `Game.handle_key()` から `pacman.controls.game_input` へ渡し、ゲームの状態・得点・残機は引き続き `Game` と各キャラクターが保持します。画面遷移は `Game.set_state()` で再描画要求も更新します。

ゲーム側のクラスから描画を分離し、`WorldRenderer` が迷路・gum・キャラクターを描きます。画像生成とキャッシュは `pacman.visualize.sprites` が担当します。移動とgumの配置は引き続きCanvasの座標変換を使いますが、型ヒントの参照だけなのでゲーム関連のimportでは描画・MLX・Pygameを読み込みません。

状態は `GameState`、赤の識別は戦略の型ではなく `GhostRole.RED` を使います。Pythonのソースはすべて `pacman/` にまとめ、`pacman.py` はルートの起動用スクリプトとして残しています。音源・フォントは引き続きルートの `assets/` に置きます。

## 検証と今後の作業

```bash
.venv/bin/python -B -m unittest discover -s tests -q
```

移動・配置・レベルサイズ変更・敵の復帰待ち・ハイスコア・画面遷移・チート・GUIの描画を、MLXのウィンドウを開かない自動テストで確認します。最新の検証結果は[PROGRESS.md](PROGRESS.md)に記録します。

課題要件への対応は継続中です。PDFとの照合結果は[REQUIREMENTS.md](REQUIREMENTS.md)、再開時の作業は[PROGRESS.md](PROGRESS.md)を参照してください。

## 数字表示と敵の点滅（2026-10-27）

HUDと無敵時間は数字・小数点の部品画像を再利用して合成し、表示項目ごとに最新の完成画像だけを保持します。中央揃えにも同じ完成画像の幅を使います。
敵は復活まで残り1.5秒から表示・非表示を切り替えます。無敵終了まで残り1.5秒では敵の青色と通常色を切り替え、どちらも切り替え間隔は0.20秒です。

## 加点値と倍率

通常gum・スーパーgumの加点値は`Game.pacgum_points`、敵は`Game.ghost_points`に設定値から初期化して保持します。`Player.update_player()`は食べたgumの種類を返し、`Game.update_game()`がその値と`score_multiplier`を使って加点します。累計得点は引き続き`player.score`で保持します。Visualizerからは`self.game.player`や`self.game.state`で参照します。

`GameVisualizer._on_loop()`は経過秒数を`Game.update_game(elapsed, canvas)`へ渡し、その結果を描画します。キーは`Game.handle_key(key, canvas)`へ渡し、終了や配色変更の要求だけVisualizerが実行します。レベル変更時はGameが迷路を生成し、VisualizerがCanvasのセルサイズ・オフセットを更新してから`Game.place_level(canvas)`でキャラクターとgumを配置します。`Game`はMLXやGUIを直接操作しません。
Xで倍率を切り替えても獲得済みの得点は変えず、以降の3種類の加点に適用します。10倍中はHUDに`x10`を表示します。チート解除・新規ゲームで倍率は1倍に戻ります。数字コマンドとの衝突がなくなったため、次レベル操作は通常のNです。

## ドットフォント

文字は同梱の`assets/fonts/PressStart2P-Regular.ttf`を読み込みます。ライセンスは同じディレクトリの`OFL.txt`を参照してください。ポーズ画面の枠幅は表示する最長の行と余白から計算し、横幅の小さい画面では説明文が収まるよう文字サイズを調整します。

## キャラクター描画

ホームには大きなタイトル・Pac-Manとghost4体・中央揃えのメニューを表示します。キャラクターは16×16の透明画像に描き、NEARESTで表示サイズへ拡大します。Ghostは足4本と白目・黒目を持ち、Playerは4方向と口の開閉に対応します。ホームとゲーム中で同じ画像生成関数を使います。

## 音声

pygame-ceのmixerでBGMとgum取得音を再生します。Home・Ranking・Instructionでは共通のメニュー曲、Playingではプレイ曲へ切り替え、同じ曲を再生中なら再読み込みしません。現時点ではPauseやクリア画面へ移動しても直前のBGMが継続します。

使用する6音源は`assets/audio/`に配置します。各ファイルと出典の対応は[音源メモ](assets/audio/README.md)を参照してください。テストは音声デバイスや音源ファイルの読み込みをモック化します。

## 音源クレジット

このゲームでは、以下の作者の皆さまが公開してくださった音楽・効果音を使用しています。素敵な音源を提供してくださった皆さまに感謝します。

| 用途 | 作品 | 作者 | 配布元 |
| --- | --- | --- | --- |
| メニューBGM | 8 bit Arcade | moodmode | [Pixabay](https://pixabay.com/music/video-games-8-bit-arcade-138828/) |
| プレイ中BGM | Chipped urgency(combat)（ループ版） | Centurion_of_war | [OpenGameArt](https://opengameart.org/content/chipped-urgencycombat) |
| gum取得音 | Retro Coin 1 | Driken5482 | [Pixabay](https://pixabay.com/sound-effects/film-special-effects-retro-coin-1-236677/) |
| Power up音 | Retro powerup 1 | Driken5482 | [Pixabay](https://pixabay.com/sound-effects/retro-powerup-1-236686/) |
| 敵を食べる音 | Retro blip | Driken5482 | [Pixabay](https://pixabay.com/sound-effects/film-special-effects-retro-blip-236676/) |
| Game over音 | Game over - retro video game 1 | ejah_music | [Pixabay](https://pixabay.com/music/video-games-game-over-retro-video-game-1-422479/) |

## フォントクレジット

画面の文字には **Press Start 2P** を使用しています。レトロなゲームの雰囲気を彩るフォントを公開してくださった作者の皆さまに感謝します。

- フォント：Press Start 2P
- 作者・著作権者：The Press Start 2P Project Authors（Copyright 2012）
- 配布元：[Google Fonts](https://fonts.google.com/specimen/Press+Start+2P)
- 同梱ライセンス：[SIL Open Font License 1.1](assets/fonts/OFL.txt)
