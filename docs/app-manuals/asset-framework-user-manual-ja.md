# ASSET Framework App 使用説明書

対象アプリ版: v2.9.0
文書版: v1.5
更新日: 2026年10月23日

<!-- pagebreak -->

## 目次

[TOC]

### このマニュアルの進み方

| ステップ | 目的 | 主な画面 |
|---|---|---|
| 1 はじめる | アプリと入力データを準備する | Prediction Workspace |
| 2 予測する | 地図または CSV から RSS を予測する | Prediction Workspace |
| 3 確認する | 結果を地図で見て CSV に保存する | Results Explorer |
| 4 深く調べる | 結果を図にして比較する | Data Analysis |
| 5 学習する | 特徴量と新しいモデルを作る | Feature Generation / Model Training |

<!-- pagebreak -->

## 1. このアプリでできること

ASSET Framework App は、電波の受信信号強度、つまり RSS を地図上で予測し、予測結果を確認し、必要に応じて新しい学習用データやモデルを作るためのアプリです。

難しい専門用語が画面に出ることがありますが、通常の利用では次の流れだけ覚えれば十分です。

1. 予測したい地域、周波数、アンテナ条件を入力します。
2. 地図または CSV ファイルで予測地点を指定します。
3. `Run RSS Prediction` を押して予測を実行します。
4. `Results Explorer` で地図表示を確認し、CSV を保存します。
5. 必要に応じて `Data Analysis` で図を作成します。

### 画面全体の考え方

左側のメニューで作業場所を切り替えます。中央が現在の作業画面、右側が実行状況と簡易ログです。

| 画面 | 主な用途 |
|---|---|
| Prediction Workspace | RSS 予測を実行する |
| Results Explorer | 最新の予測結果を地図で見る、CSV を保存する |
| Model Training | 新しいモデル、転移学習モデル、追加学習モデルを作る |
| Feature Generation | 測定 CSV や地図データから学習用特徴量を作る |
| Data Analysis | 予測 CSV を分析し、図を SVG/PNG で保存する |
| Log Console | 実行ログ、警告、エラーを確認する |
| Reference | 研究上の参考文献を確認する |

![実際の ASSET Framework App 起動画面（初回ガイド表示例）](assets/prediction-workspace.png)

画面左側で機能を選び、中央で設定と操作を行います。初回ガイドが表示された場合は、`Next` で各機能の位置を確認するか、`Skip` で閉じてください。

<!-- pagebreak -->

## 2. 利用前に準備するもの

すべての機能を一度に使う必要はありません。まず予測だけを行う場合は、地域、周波数、アンテナ位置が分かれば始められます。

### RSS 予測に必要なもの

| 項目 | 説明 |
|---|---|
| Base Model | 通常は `General Model M0 (Shinshu Univ. & NICT 202605)` を選びます。独自モデルを使う場合は `Custom Model` を選びます。 |
| Database | 予測対象地域の地図データです。例: Nagano Matsumoto, Okinawa Naha など。一覧にない地域が必要な場合は、アプリ開発会社へお問い合わせいただくか、今後の更新をお待ちください。 |
| Prediction Data | 地図範囲から作るか、CSV ファイルから読み込むかを選びます。 |
| Frequency in MHz | 使用する無線周波数です。例: 920。 |
| SF | LoRa の Spreading Factor です。不明な場合や使わない場合は `None` を選びます。 |
| EIRP in dBm | 送信条件を表す値です。分からない場合は管理者または測定担当者に確認してください。 |
| Fixed Longitude / Latitude | 固定アンテナの経度と緯度です。 |
| Fixed Elevation / Fixed Height / Mobile Height | アンテナの高さ条件です。 |

### CSV ファイルを使う場合

予測地点を CSV で指定する場合、CSV には経度と緯度の列が必要です。

| 種類 | 使用できる列名の例 |
|---|---|
| 経度 | `longitude`, `lon`, `lng`, `x` |
| 緯度 | `latitude`, `lat`, `y` |
| RSSI | 予測 CSV では任意。学習用 CSV では必要です。列名例: `RSSI`, `rssi` |

### アンテナ高さの見方

次の図は、画面上の `Fixed Elevation`, `Fixed Height`, `Mobile Height` の関係を示します。

![固定局と移動局の高さの考え方](../../web/assets/help/antenna-height-reference.png)

| 項目 | 意味 |
|---|---|
| Fixed Elevation | 固定局の設置地点そのものの標高です。 |
| Fixed Height | 設置地点から固定アンテナまでの高さです。 |
| Mobile Height | 移動側アンテナの地面または車両基準からの高さです。 |

<!-- pagebreak -->

## 3. アプリを起動して画面を確認する

アプリを起動すると、最初に ASSET の画面が表示されます。初回は画面案内が出る場合があります。

### 初回ガイド

画面案内では、左メニューや主要ボタンの位置が順番にハイライトされます。

- `Next` を押すと次の説明に進みます。
- `Back` を押すと前の説明に戻ります。
- `Skip` を押すと案内を閉じます。
- `Do not show this guide again` にチェックすると、次回から同じ案内を表示しません。

### 右側の Runtime Monitor

右側の `Runtime Monitor` は、現在の処理の進み具合を表示します。

| 表示 | 意味 |
|---|---|
| Ready | 何も実行していない状態です。 |
| 30%, 40%, 70% など | 予測や学習が進行中です。 |
| Completed | 処理が正常に終わりました。 |
| Error | 何らかの問題で処理が止まりました。 |

処理中に画面が一部操作できなくなることがあります。これは、途中で条件が変わって結果が壊れないようにするためです。

<!-- pagebreak -->

## 4. RSS 予測を実行する

RSS 予測は `Prediction Workspace` で行います。通常はこの画面から作業を始めます。

### 4.1 地図範囲で予測する

地図上の範囲を使って予測する場合は、次の手順で操作します。

1. 左メニューで `Prediction Workspace` を開きます。
2. `Base Model` で使用するモデルを選びます。通常は `General Model M0 (Shinshu Univ. & NICT 202605)` です。
3. `Database` で対象地域を選びます。
4. `Prediction Data` を `Map bounds` にします。
5. `Mesh Longitude` と `Mesh Latitude` を入力します。値が大きいほど細かく予測できますが、処理時間も長くなります。
6. 周波数、SF、EIRP、アンテナ位置、高さを入力します。
7. `Draw Area` を押し、地図左側の矩形または円形ツールで予測したい範囲を指定します。
8. `Run RSS Prediction` を押します。
9. `Runtime Monitor` が `Completed` になるまで待ちます。

> [SUCCESS] `Runtime Monitor` に `Completed` と表示され、`Results Explorer` に `New` が表示されれば予測完了です。

> [WARNING] メッシュ数を大きくすると細かく予測できますが、処理時間と使用メモリも増えます。初回は既定値のまま試してください。

<!-- pagebreak -->

### 4.1.1 矩形・円形の選択と寸法表示

`Prediction Area` では、次の 2 種類の選択方法を利用できます。選択できる範囲は 1 つです。新しい範囲を描くと、前の選択が置き換わります。

| 選択方法 | 操作と表示 |
|---|---|
| 矩形 | 地図左側の矩形アイコンを選び、対角の 2 点を指定します。下辺に `Width`（横幅）、右辺に `Height`（縦幅）が表示されます。 |
| 円形 | 円形アイコンを選び、中心から外側へドラッグして半径を指定します。半径の補助線と `Radius`（半径）が表示されます。 |

寸法は地表上の距離の目安で、1,000 m 未満は `m`、それ以上は `km` で表示されます。画面上のピクセル数ではありません。

- 編集ツールで変更を確定すると、寸法表示も更新されます。
- 削除ツールで削除を確定すると、範囲と寸法表示が消えます。実行前に新しい範囲を選択してください。
- `Reset` でも範囲と寸法表示が消去されます。再利用したい場合は、先に `Save Params` を押してください。

> [CHECK] 円形では、外接矩形に `Mesh Longitude` × `Mesh Latitude` の格子を作り、円の外側の点を除いて予測します。実際の予測点数は両者の積より少なくなります。円内に格子点がない場合はエラーが表示されるため、両方のメッシュ数を増やしてください。

範囲指定は `Map bounds` の場合のみ使用します。CSV 入力の地点は円形や矩形で絞り込まれません。

<!-- pagebreak -->

### 4.2 CSV ファイルで予測する

予測したい地点が CSV として用意されている場合は、次の手順で操作します。

1. `Prediction Data` を `CSV file selected by native dialog` にします。
2. モデル、地域、周波数、アンテナ条件を入力します。
3. `Run RSS Prediction` を押します。
4. ファイル選択画面が出たら、予測地点 CSV を選びます。
5. `Runtime Monitor` が `Completed` になるまで待ちます。

CSV で予測する場合、地図上の範囲指定は使いません。CSV の経度・緯度列が予測地点になります。

### 4.3 パラメータを保存して再利用する

同じ条件で何度も試す場合は、`Save Params` と `Reload Params` を使います。

| ボタン | 用途 |
|---|---|
| Save Params | 現在の入力値と選択範囲を一時保存します。円形の場合は中心と半径も保存します。 |
| Reload Params | 保存した入力値・選択範囲・寸法表示を復元します。Reset 後も再利用できます。 |
| Reset | 実行中の予測を停止し、予測画面の一時状態を整理します。 |

<!-- pagebreak -->

## 5. 予測結果を見る、CSV を保存する

予測が完了すると、左メニューの `Results Explorer` に `New` の表示が出る場合があります。

### 5.1 最新結果を読み込む

1. 左メニューで `Results Explorer` を開きます。
2. `Load Latest Result` を押します。
3. 地図上に予測結果が表示されることを確認します。

### 5.2 表示を切り替える

結果地図では、次の表示を切り替えられます。

| 表示 | 説明 |
|---|---|
| Prediction RSS | 予測された RSS の強さを色で表示します。 |
| Uncertainty | 予測の不確実さを表示します。 |
| Sampling Suggestions | 予測結果から追加測定の候補地点を選び、地図表示と CSV 保存を行います。 |

`Uncertainty` では `η` の値で、上位・下位の判定範囲を調整できます。専門的な判断が必要な場合は、研究担当者または管理者の指示値を使ってください。

### 5.3 CSV を保存する

1. `Results Explorer` で `Download CSV` を押します。
2. 保存先を選びます。
3. 保存された CSV を表計算ソフトや `Data Analysis` で利用します。

> [SUCCESS] 保存先に CSV ファイルが作成され、表計算ソフトで経度・緯度・予測値の列を確認できれば完了です。

`Download CSV` は、アプリ内部に残っている最新の予測結果を保存します。複数回予測した場合は、最後に成功した結果が対象です。

### 5.4 出力 CSV の列

| 列名 | 意味 |
|---|---|
| Latitude | 緯度。予測地点の南北方向の位置です。 |
| Longitude | 経度。予測地点の東西方向の位置です。 |
| RSSI | 実測した RSS 値です。実測値がない予測用データでは占位値が入る場合があります。 |
| DN | 予測地点の海抜高度です。 |
| FresnelR_H | 水平方向のフレネル半径です。 |
| FresnelR_V | 垂直方向のフレネル半径です。 |
| disBtwTxRx | 送信アンテナと受信アンテナの空間距離です。 |
| Model_0 | 0 号モデルが出力した予測 RSS 値です。 |
| Model_1 | 1 号モデルが出力した予測 RSS 値です。 |
| Predicted_Value | 全モデルが出力した予測 RSS 値の中央値です。 |
| Uncertainty | 全モデルの予測結果から求めた不確実さです。 |
| pathLoss_eta_2 | 古典的な距離減衰モデルによる自由空間向けの予測 RSS 値です。 |
| pathLoss_eta_3 | 古典的な距離減衰モデルによる都市環境向けの予測 RSS 値です。 |

<!-- pagebreak -->

### 5.5 追加測定の候補地点を選ぶ

`Sampling Suggestions` は、読み込んだ予測結果から測定候補地点を選ぶ機能です。矩形・円形の地図範囲による予測結果にも、CSV 地点による予測結果にも利用できます。

1. `Results Explorer` の `Load Latest Result` で予測結果を読み込みます。
2. `Result Map` の `Sampling Suggestions` を選びます。
3. `Method` でアルゴリズムを選びます。隣の `?` にマウスを重ねると、選択中の方式の説明が表示されます。キーボードで `?` にフォーカスしても確認できます。
4. `Budget Type` を割合または地点数に設定し、`Budget` を入力します。既定値は 10% です。
5. 必要に応じて初期間隔と `Advanced Parameters` を設定し、`Generate Suggestions` を押します。
6. 地図の橙色の推薦点を確認し、この欄の `Download CSV` で保存します。

緯度と経度が完全に一致するレコードは、すべての方式で選点前に除外します。同じ地点の最初のレコードを残し、値の平均化は行いません。割合の予算は重複除去後の地点数を基準に計算し、小数点以下を切り捨てます。選択数が 0 になる場合は予算を増やしてください。

| 地図の推薦点をクリックしたときの表示 | 内容 |
|---|---|
| Selection / Latitude / Longitude | 選択順序と緯度・経度です。 |
| Predicted_Value in dBm | その地点の予測 RSS 値です。 |
| Uncertainty in dB | その地点の不確実さです。 |

欠損値や無効値、占位値 `-999` は `N/A` と表示されます。選択順序は道路上の巡回順序を保証するものではありません。

出力 CSV は選択されたレコードの元の列を保持し、`Sampling_Order`（1 からの選択順序）と `Sampling_Method`（方式名）を追加します。元データに `SampleID` がない場合は内部 ID も出力されます。`Reset` は推薦点と選択結果を消し、サンプリング設定を既定値に戻します。予測結果そのものは消しません。設定変更または予測結果の再読み込みでも、以前の推薦結果は無効になります。

<!-- pagebreak -->

### 5.6 サンプリング方式の選び方

全 11 方式を利用できます。不確実さを利用する方式には、有限かつ 0 以上の `Uncertainty` が必要です。座標のみを使用する方式では不要です。

| Method | 簡単な説明 |
|---|---|
| URAS | 不確実さの高・中・低層（20/60/20%）に分け、各層で DBSCAN による領域を選択します。初期配分は 70/20/10%。不足分は未選択点の不確実さが高い順に補います。 |
| URAS-Spatial | 不確実さの層と複数の空間クラスタを使い、選択点間の最小間隔も考慮します。必要に応じて間隔を緩和して予算を満たします。 |
| Random | 重複除去後の地点から無作為に、同じ地点を繰り返さず選びます。seed により再現できます。 |
| Top-U | 不確実さが高い地点から選びます。空間的な分散や最小間隔は保証しません。 |
| Bottom-U | 不確実さが低い地点から選びます。空間的な分散や最小間隔は保証しません。 |
| Spatial k-center | seed で最初の地点を選び、以後は既選択点から最も離れた候補を追加します。座標のみで空間的な広がりを重視します。 |
| Spatial GP | 固定空間カーネルのガウス過程の条件付き分散に基づく選点です。座標のみを使い、実測 RSSI や委員会の不確実さは使用しません。 |
| DBSCAN-NN | 座標でクラスタを作り、指定開始位置から最近傍の巡回を用いて選点します。道路経路ではなく、最短経路も保証しません。 |

`Other Methods`（その他の方法）には、要素の有無を比較する次の 3 方式があります。

| Method | 簡単な説明 |
|---|---|
| URAS-noU | 不確実さを使わず、大きな空間クラスタから座標順に選びます。最小間隔の制約はありません。 |
| URAS-noDBSCAN | 不確実さの層と初期配分を残し、DBSCAN による領域選択を省略します。不足分を全体から補います。 |
| URAS-Spatial-noU | 不確実さを使わず、空間クラスタと最小間隔を使います。間隔を段階的に緩和できます。 |

> [CHECK] 同じ入力と設定では再現可能な結果になります。Random、Spatial k-center、Spatial GP の初期選択は seed に依存します。方式名だけで予測精度の優劣が決まるわけではありません。

<!-- pagebreak -->

### 5.7 間隔と詳細パラメータ

| 設定 | 意味と既定値 |
|---|---|
| Budget Type / Budget | 割合または地点数。既定値は 10%。地点数の場合は 1 以上の整数を入力します。 |
| Initial spacing in m | URAS-Spatial と URAS-Spatial-noU の初期間隔。既定値は 30 m。入力範囲は 0～10,000 m です。 |
| DBSCAN epsilon in degrees | DBSCAN の近傍半径。既定値は 0.0008 度で、メートルではありません。 |
| DBSCAN minimum samples | DBSCAN の密度判定に必要な点数。既定値は 20 です。 |
| Random seed | Random、Spatial k-center、Spatial GP の乱数 seed。既定値は 42 です。 |
| GP length scale in m | Spatial GP の固定空間カーネルの長さ尺度。既定値は 100 m です。 |
| Start latitude / longitude in degrees | DBSCAN-NN の開始位置。予測画面の固定アンテナ座標から初期設定されるため、使用前に確認します。 |

選択中の方式に不要な設定は無効になります。`Advanced Parameters` を開くと詳細設定を確認できます。

**URAS-Spatial の補点規則**

最初は入力した間隔を使い、すべての既選択点からその間隔より遠い候補を選びます。予算に届かなければ既選択点を保持し、10 m ずつ間隔を減らして補います。次の間隔が 10 m 未満になる場合は、間隔制限なしで補います。

- 初期値 30 m：30 m → 20 m → 10 m → 制限なし。
- 初期値 25 m：25 m → 15 m → 制限なし。5 m の段階は実行しません。
- 初期値が 10 m 未満：最初から間隔制限なし。

予算を満たした時点で終了します。結果欄に実行した各段階と追加地点数が表示され、`Unrestricted` は間隔制限なしを意味します。URAS-Spatial-noU も同じ間隔緩和を使います。最終的な点間隔が初期値を下回る場合がありますが、重複地点が再び追加されることはありません。

> [WARNING] Spatial GP は候補 20,000 地点以下かつ選択 500 地点以下に制限されています。超過時は予算・候補範囲を減らすか、別方式を選んでください。GP の分散は校正済みの RSS 誤差や確率的な信頼区間ではありません。すべての方式で選点に実測 RSSI は使わず、実測や再学習も自動実行しません。推薦点へ行く前に立入可否、道路、地形、安全性を確認してください。

<!-- pagebreak -->

## 6. Feature Generation で学習用データを作る

`Feature Generation` は、測定 CSV や地図データを使って、モデル学習で使う特徴量ファイルを作る画面です。

### 6.1 入力ファイル

| ファイル | 必須 | 説明 |
|---|---:|---|
| Training CSV | 必須 | 測定点の経度、緯度、RSSI を含む CSV です。 |
| Altitude TIFF | 必須 | 標高や地形を表す TIFF ファイルです。 |
| Building GPKG | 任意 | 建物データです。遮蔽や周辺環境の特徴作成に使います。生成には専用の地理データ処理が必要です。 |
| Land-use GPKG | 任意 | 用途地域や土地利用のデータです。生成には専用の地理データ処理が必要です。 |

> [WARNING] `Building GPKG` と `Land-use GPKG` の新規生成は、本 APP の通常機能には含まれません。必要な場合はアプリ開発会社へお問い合わせください。

### 6.2 操作手順

1. 左メニューで `Feature Generation` を開きます。
2. `Dataset Parameters` に周波数、SF、EIRP、固定局位置、高さを入力します。
3. `Training CSV` を押して測定 CSV を選びます。
4. `Altitude TIFF` を押して標高 TIFF を選びます。
5. 必要に応じて `Building GPKG (Optional)` と `Land-use GPKG (Optional)` を選びます。
6. `Upload and Process` を押します。
7. 完了後、`Download Output` が表示されたら押して保存します。

### 6.3 CSV が読み込めないとき

CSV の列名が合わない、空の値が多い、ファイル形式が違う場合は、処理が失敗または一部スキップされます。

最低限、学習用 CSV には次の列が必要です。

| 種類 | 列名例 |
|---|---|
| 経度 | `longitude`, `lon`, `lng`, `x` |
| 緯度 | `latitude`, `lat`, `y` |
| 測定 RSSI | `RSSI`, `rssi` |

<!-- pagebreak -->

## 7. Model Training でモデルを作る

`Model Training` は、特徴量ファイルを使って新しいモデルや転移学習モデルを作る画面です。

### 7.1 まず Feature Vector を用意する

モデル学習には特徴量ファイルが必要です。まだ用意していない場合は、`Open Feature Generation` を押して先に特徴量を作成します。

既に `.xz` 形式の特徴量ファイルがある場合は、`Feature Vector Mode` を `Use existing feature vectors` にして、`Select *.xz Feature Vectors` から選択します。

### 7.2 モデル設定の意味

| 項目 | 説明 |
|---|---|
| Feature Vector Mode | 特徴量を新しく作るか、既存の `.xz` ファイルを使うかを選びます。 |
| Scheduler | 分散実行する場合の Dask scheduler アドレスです。空欄ならローカル実行です。 |
| Base Model | 新規学習、一般モデルからの転移学習、独自モデルからの転移学習を選びます。 |
| Kernel Count | 学習に使用するカーネル数です。値を大きくするとモデル性能が高くなる傾向がありますが、学習速度は低下します。推奨値は `16` です。 |
| Learning Type | 学習方法を選びます。既存モデルを新しい地域や条件へ適応させる場合は `Transfer Learning`、新しいデータを加えて学習を継続する場合は `Incremental Training` を選びます。新規モデルでは `None` を使用します。 |
| Train Judge Model | 転移モデルの性能を判定するための判断モデルを同時に学習します。On にすると計算量が大幅に増えます。主に研究用途向けのため、目的が明確でない場合は Off を推奨します。 |
| Freeze Layer | 転移学習で固定する層を指定します。通常は既定値を使います。 |
| Learning Rate | 学習率の初期値です。通常は既定値 `0.0001` を使います。プログラムは学習の進行に合わせて値を自動的に小さくし、モデルの学習完了まで調整します。 |

### 7.3 学習を実行する

1. `Model Training` を開きます。
2. 特徴量ファイルを用意します。
3. `Base Model` と `Learning Type` を選びます。
4. 分散実行しない場合は `Scheduler` を空欄にします。
5. `Generate Model` を押します。
6. `Runtime Monitor` が `Completed` になるまで待ちます。
7. 保存ダイアログが表示されたら、生成モデルを保存します。

### 7.4 分散実行を使う場合

複数台の PC やサーバで Dask を使う場合は、`Open Guide` を押して手順を確認します。

`Scheduler` には、例として `tcp://host:8786` または `host_ip:8786` の形式で入力します。接続できない場合、アプリはローカル実行に戻ることがあります。

### 7.5 First-Person View で学習状況を見る

`Model Training` 画面の `First-Person View` を押すと、`Neural Training Observatory` が全画面で開きます。学習の状態とアプリの実行ログを、3D のデジタルツイン表現と一緒に確認できます。

| 操作 | 説明 |
|---|---|
| Signal field | 電波強度をイメージした色付き表示の On / Off を切り替えます。 |
| Opacity | Signal field の透明度を調整します。 |
| Train Window View | 列車が通過している間、車窓からの視点へ切り替えます。 |
| Aircraft Window View | 航空機が通過している間、機内からの視点へ切り替えます。 |
| Boat View | 船が通過している間、船上からの視点へ切り替えます。 |
| Exit View | 3D 表示を閉じて `Model Training` 画面へ戻ります。 |

車両や航空機が観測位置にない間は、対応する視点ボタンを押せない場合があります。しばらく待つと利用可能になります。各乗車視点からは同じボタンをもう一度押すと観測画面へ戻れます。

> [TIP] この画面は学習状況を分かりやすく見るための説明用可視化です。モデルの出力や学習内容には影響しません。3D が表示できない場合も、モデル学習はそのまま継続します。

## 8. Data Analysis で図を作成する

`Data Analysis` は、予測結果 CSV を分析し、報告書や論文に使える図を作る画面です。

### 8.1 基本手順

1. 左メニューで `Data Analysis` を開きます。
2. `Prediction CSV Analyzer` が選ばれていることを確認します。
3. `Select Folder` を押し、予測 CSV が入っているフォルダを選びます。
4. 一覧から分析に使う CSV にチェックを入れます。
5. 必要に応じて色を選びます。
6. `Analysis Type` で作りたい図や表を選びます。
7. `Run Analysis` を押します。
8. 画面下部の `Analysis Output` で結果を確認します。
9. `Download SVG` または `Download PNG` を押して保存します。

> [TIP] 拡大して印刷する資料には SVG、メールやスライドに貼る場合は PNG が扱いやすいです。

### 8.2 選べる分析

| Analysis Type | 何を見るためのものか |
|---|---|
| RSSI CDF | RSSI の分布を確認します。 |
| Predicted Value CDF | 予測値の分布を確認します。 |
| Uncertainty CDF | 不確実さの分布を確認します。 |
| Absolute Error CDF | 誤差の大きさの分布を確認します。 |
| Model Error Box Plot | 複数モデルの誤差を箱ひげ図で比較します。 |
| Summary Statistics Table | 平均、中央値などの統計表を作ります。 |
| Predicted vs RSSI Scatter Plot | 実測値と予測値の関係を散布図で確認します。 |
| Error vs Distance Plot | 距離と誤差の関係を見ます。 |
| Error vs Altitude / Fresnel Features | 標高やフレネル関連特徴と誤差の関係を見ます。 |
| Path Loss Baseline Comparison | パスロス基準との比較をします。 |
| Uncertainty Calibration Plot | 不確実さが誤差と対応しているか確認します。 |
| Model Ensemble Violin Plot | モデル群のばらつきを比較します。 |
| Spatial Error Map | 誤差を地理的に確認します。 |

### 8.3 分析できない CSV がある場合

分析ごとに必要な列は異なります。アプリは、必要な列がない CSV をスキップし、理由を表示します。

1つの CSV がスキップされても、ほかの CSV が有効なら分析は続きます。エラーが出た場合は、`Log Console` で詳細を確認してください。

<!-- pagebreak -->

## 9. Log Console を使う

`Log Console` は、アプリ内部の処理状況、警告、エラーを確認する場所です。

### 9.1 ログを見る

左メニューで `Log Console` を開くと、アプリの実行ログを大きな画面で確認できます。右側の `Compact Log` から `Open` を押して開くこともできます。

### 9.2 ログを保存する

1. `Export Log` を押します。
2. 保存先を選びます。
3. `ASSET_application_log_YYYYMMDD_HHMMSS.txt` のような名前で保存されます。

問い合わせや不具合報告をする場合は、保存したログを添付すると原因調査が進みやすくなります。

### 9.3 ログを消す

`Clear Logs` を押すと画面上のログ表示を消せます。処理結果そのものを削除する操作ではありません。

<!-- pagebreak -->

## 10. よくある質問と困ったとき

### 予測結果が表示されません

まず `Results Explorer` で `Load Latest Result` を押してください。それでも表示されない場合は、予測が最後まで完了していない可能性があります。`Log Console` でエラーを確認してください。

### `Download CSV` を押しても保存できません

最新の予測結果がアプリ内部にない可能性があります。もう一度 `Run RSS Prediction` を実行し、完了後に保存してください。

### CSV が選べるのに処理で失敗します

ファイル拡張子が `.csv` でも、必要な列がないと処理できません。経度、緯度、必要に応じて RSSI の列名を確認してください。

### 処理中に別画面へ移動できません

予測、特徴量生成、モデル学習の実行中は、条件変更を防ぐため一部の画面移動が制限されます。ログ画面は確認できます。

### 処理を止めたいです

現在の作業画面に戻り、`Reset` を押してください。実行中の予測または学習を停止し、一時状態を整理します。

### `Custom Model` を選んだらファイル選択が出ます

`Custom Model` には、本ソフトウェアで生成したモデルのみ使用できます。他のソフトウェアや異なる形式で作成したモデルには対応していません。通常利用では `General Model M0 (Shinshu Univ. & NICT 202605)` を選んでください。

### 分析図は SVG と PNG のどちらで保存すべきですか

報告書や論文で拡大して使う場合は SVG が向いています。スライド、メール、一般的な資料に貼る場合は PNG が扱いやすいです。

<!-- pagebreak -->

## 11. 用語集

| 用語 | やさしい説明 |
|---|---|
| RSS | 受信した電波の強さです。値が大きいほど受信しやすい傾向があります。 |
| RSSI | RSS とほぼ同じ意味で使われる受信強度の値です。 |
| EIRP | 送信機とアンテナを含めた送信の強さを表す値です。 |
| SF | LoRa 通信で使う Spreading Factor です。通信距離や速度に関係します。 |
| Mesh | 地図を細かい格子に分けて予測するための点や範囲です。 |
| Feature Vector | モデル学習に使う特徴量データです。 |
| Transfer Learning | 既存モデルを使って、新しい地域や条件に合わせて調整する学習方法です。 |
| Incremental Training | 既存モデルに新しいデータを追加して学習を続ける方法です。 |
| Dask | 複数の CPU や複数台のコンピュータで処理を分担する仕組みです。 |
| Uncertainty | 予測結果の不確実さです。値が大きい場所は追加測定の候補になります。 |
| CDF | 値の分布を確認するグラフです。 |
| GPKG | 地図データを保存する GeoPackage 形式です。 |

<!-- pagebreak -->

## 12. 推奨ワークフロー

初めて使う場合は、次の順番がおすすめです。

1. `Prediction Workspace` で既存の `General Model M0` を使い、対象地域の RSS 予測を試します。
2. `Results Explorer` で地図を確認し、CSV を保存します。
3. `Data Analysis` で RSSI CDF や Uncertainty CDF を作り、結果の傾向を確認します。
4. 実測データが増えたら `Feature Generation` で特徴量を作ります。
5. `Model Training` で転移学習モデルを作ります。
6. 新しいモデルで再度予測し、結果を比較します。

重要なのは、予測と分析を一度で終わらせないことです。結果地図と不確実さを見ながら、測定、学習、再予測を繰り返すことで精度を高めます。

<!-- pagebreak -->

## 13. 更新履歴

| 日付 | 文書版 | 内容 |
|---|---|---|
| 2026年10月23日 | v1.5 | 対象アプリを v2.9.0 に更新。Sampling Suggestions の 11 方式、重複地点除去、予算、間隔緩和、説明 tip、推薦点の予測値・不確実さ表示、CSV 保存を追加。 |
| 2026年9月30日 | v1.4 | Prediction Area の円形選択、幅・高さ・半径の表示、円内の格子点による予測、選択範囲の保存・復元を追加。 |
| 2026年9月17日 | v1.3 | 対象アプリを v2.8.4 に更新。一般モデルの表示名、Incremental Training の利用方法、Model Training の First-Person View と列車・航空機・船舶視点を追加。 |
| 2026年9月8日 | v1.2 | ヒラギノ角ゴシックへ変更。全面表紙、実画面、CSV 列説明、モデル学習および地域データに関する注意事項を追加。用語を「不確実さ」に統一。 |
| 2026年9月8日 | v1.1 | Visual Quickstart 版へ改訂。表紙、目次、手順表示、表、ページナビゲーションを再設計。 |
| 2026年9月8日 | v1.0 | ASSET Framework App の現行画面に合わせて、一般利用者向けの日本語使用説明書を新規作成。Prediction Workspace、Results Explorer、Feature Generation、Model Training、Data Analysis、Log Console、用語集、FAQ を追加。 |

## 14. サポート時に伝える情報

問い合わせや不具合報告をする場合は、次の情報を伝えると確認が早くなります。

- 使用している OS
- アプリ画面に表示されているバージョンまたは `Development Build` 表示
- 実行した画面名
- 入力した Database、Frequency、Prediction Data の種類
- エラーが出た場合は `Export Log` で保存したログ
- 使用した CSV の列名

この説明書の更新日: 2026年10月23日
