import os
import re
import shutil
from collections import defaultdict

# 対象ディレクトリ
data_dir = "data/raw/uniswap"
archive_dir = "data/raw/uniswap/archived"

# archived ディレクトリがなければ作成
os.makedirs(archive_dir, exist_ok=True)


# ファイル名から時間単位のキーを抽出する関数
def extract_hour_key(filename):
    # YYYY-MM-DD形式の場合
    if re.match(r"\d{4}-\d{2}-\d{2}_pool\.jsonl", filename):
        date_part = filename.split("_")[0]
        return date_part + "T000000"  # デフォルトで00時を割り当て

    # YYYYMMDDTHHMMSSの形式の場合
    elif re.match(r"\d{8}T\d{6}_pool\.jsonl", filename):
        datetime_part = filename.split("_")[0]
        # 時間部分までを抽出（分・秒を切り捨て）
        return datetime_part[:11] + "0000"


# 1時間単位でファイルをグループ化
hour_groups = defaultdict(list)
for filename in os.listdir(data_dir):
    if filename.endswith("_pool.jsonl") and os.path.isfile(os.path.join(data_dir, filename)):
        hour_key = extract_hour_key(filename)
        if hour_key:
            hour_groups[hour_key].append(filename)

# 重複がある時間帯を処理
for hour_key, files in hour_groups.items():
    if len(files) > 1:
        # ソートして最新（またはファイル名順で最後）のファイルを特定
        files.sort()
        keep_file = files[-1]  # 最後のファイルを残す

        print(f"時間帯 {hour_key} の重複: {files}")
        print(f"  → 残すファイル: {keep_file}")

        # 残す以外のファイルをアーカイブ
        for file in files:
            if file != keep_file:
                src = os.path.join(data_dir, file)
                dst = os.path.join(archive_dir, file)
                print(f"  → アーカイブ: {file}")
                shutil.move(src, dst)
