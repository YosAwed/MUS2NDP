#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MUS to NDP MML Converter

MUS形式音楽ファイルをNDP互換のMML形式に変換するツール
バージョン: 1.1.0

変更履歴:
- v1.1.0: テンポ変換機能の追加、ループコマンドの@L形式への変換、非互換コマンド(D, p)の削除
- v1.0.0: 初期リリース
"""

import re
import os
import sys

# グローバル定数
MUS_TO_NDP_TRACK_MAP = {
    'A': '1', 'B': '2', 'C': '3', 'D': '4', 'E': '5', 'F': '6', 'G': '7', 'H': '8'
}

NDP_TIMEBASE = 48  # NDP MMLのデフォルトタイムベース
MAX_LINE_LENGTH_MMLE = 80  # MML Editorの1行あたりの最大文字数

def parse_mus_file(content, verbose=False):
    """
    MUSファイルの内容をパースして、トラックデータとメタデータを抽出します。
    
    Args:
        content: MUSファイルの内容
        verbose: デバッグ情報を表示するかどうか
    Returns:
        dict: タイトル、作曲者、トラックデータなどを含む辞書
    """
    if verbose:
        print(f"DEBUG parse_mus_file: Starting with verbose={verbose}")
        
    result = {
        'title': '', 
        'composer': '', 
        'tracks': {}, 
        'track_instruments': {}, 
        'voice_definitions': {}, 
        'mus_tempo': None
    }
    
    current_track = None
    track_data_list_for_current_track = []
    VALID_MUS_TRACK_CHARS = "ABCDEFGH"

    lines = content.splitlines()
    for i, line_raw in enumerate(lines):
        line_num_for_debug = i + 1
        line_stripped = line_raw.strip()

        if verbose:
            print(f"DEBUG parse_mus_file: Processing line {line_num_for_debug}: '{line_stripped[:50]}'...")

        # 空行とコメント行のスキップ処理
        if not line_stripped or line_stripped.startswith(';') or line_stripped.startswith('*'):
            if verbose:
                print(f"DEBUG parse_mus_file: Skipping comment/empty line {line_num_for_debug}")
            continue

        # タイトルと作曲者の抽出
        if line_stripped.upper().startswith("#TITLE"):
            result['title'] = line_stripped[len("#TITLE"):].strip().replace('"', '')
            if verbose: 
                print(f"DEBUG parse_mus_file: Found Title: {result['title']}")
            continue
            
        if line_stripped.upper().startswith("#COMPOSER"):
            result['composer'] = line_stripped[len("#COMPOSER"):].strip().replace('"', '')
            if verbose: 
                print(f"DEBUG parse_mus_file: Found Composer: {result['composer']}")
            continue
        
        # 音色定義の処理（例: "@ 69={ ... }"）
        if line_stripped.startswith('@') and '=' in line_stripped and '{' in line_stripped and '}' in line_stripped:
            parts = line_stripped.split('=', 1)
            inst_id_key = parts[0].strip()  # e.g. "@ 69"
            inst_data_str = parts[1].strip()
            if inst_data_str.startswith('{') and inst_data_str.endswith('}'):
                result['voice_definitions'][inst_id_key] = inst_data_str
                if verbose: 
                    print(f"DEBUG parse_mus_file: Found Voice Definition for {inst_id_key}")
            continue

        # トラックデータ処理
        line_starts_with_track_char = False
        potential_track_id = ''
        if line_stripped and line_stripped[0].isalpha() and line_stripped[0].isupper() and line_stripped[0] in VALID_MUS_TRACK_CHARS:
            line_starts_with_track_char = True
            potential_track_id = line_stripped[0]

        if line_starts_with_track_char:
            data_after_potential_track_id = line_stripped[1:]  # 先頭のトラック文字の後のデータ
            
            # 定義コマンド（@t, @NN）がデータ部分にあるかチェック
            is_definition_command_present = '@t' in data_after_potential_track_id or \
                                           bool(re.search(r"@\s*\d+(?!\s*=)", data_after_potential_track_id.lstrip()))

            if current_track is None or potential_track_id != current_track or is_definition_command_present:
                # ケース1: 完全に新しいトラック、別のトラック、または現在のトラックの再定義
                if verbose:
                    print(f"DEBUG parse_mus_file: Detected new/redefined track: '{line_stripped[:50]}'...")
                    
                # 以前のトラックデータを保存
                if current_track is not None and track_data_list_for_current_track:
                    data_to_save = ' '.join(track_data_list_for_current_track).strip()
                    if data_to_save:
                        result['tracks'][current_track] = data_to_save
                        if verbose:
                            print(f"DEBUG parse_mus_file: Saved data for track '{current_track}'")
                
                # 新しいトラックの処理を開始
                current_track = potential_track_id
                track_data_list_for_current_track = []  # リセット
                if verbose:
                    print(f"DEBUG parse_mus_file: Starting/redefined track '{current_track}'")

                # トラック行からテンポと楽器情報を処理
                processed_data, track_instruments, mus_tempo = preprocess_and_extract_data_from_track_line(
                    data_after_potential_track_id.lstrip(), 
                    current_track,
                    result['track_instruments'],
                    verbose=verbose
                )
                
                # 初めて見つかったテンポを保存
                if mus_tempo is not None and result['mus_tempo'] is None:
                    result['mus_tempo'] = mus_tempo
                    if verbose:
                        print(f"DEBUG parse_mus_file: Stored initial MUS tempo: {result['mus_tempo']}")

                if processed_data:
                    track_data_list_for_current_track.append(processed_data)
            else:
                # ケース2: 同じトラック文字で始まるが、再定義ではない継続行
                processed_data, _, _ = preprocess_and_extract_data_from_track_line(
                    data_after_potential_track_id.lstrip(),
                    current_track,
                    result['track_instruments'],
                    verbose=verbose
                )
                if processed_data:
                    track_data_list_for_current_track.append(processed_data)
        elif line_stripped:  # トラック文字以外で始まる非空白行
            if current_track is not None:  # 現在処理中のトラックがある場合
                # 直前のトラックデータの続きとして扱う
                track_data_list_for_current_track.append(line_stripped)
                if verbose:
                    print(f"DEBUG parse_mus_file: Appended non-track-prefixed line to track '{current_track}'")
    
    # 最後のトラックデータを保存
    if current_track is not None and track_data_list_for_current_track:
        data_to_save = ' '.join(track_data_list_for_current_track).strip()
        if data_to_save:
            result['tracks'][current_track] = data_to_save
            if verbose:
                print(f"DEBUG parse_mus_file: Saved final track data for '{current_track}'")
    
    if verbose:
        print(f"DEBUG parse_mus_file: Parsing complete. Found {len(result['tracks'])} tracks")
        if result['mus_tempo'] is not None:
            print(f"DEBUG parse_mus_file: MUS tempo: {result['mus_tempo']}")
    
    return result

def preprocess_and_extract_data_from_track_line(line_content, track_char, track_instruments_dict, verbose=False):
    """
    トラック行からテンポや楽器指定を抽出し、トラックデータを前処理します。
    
    Args:
        line_content: 処理するトラック行の内容（トラック文字の後の部分）
        track_char: トラック文字（例: 'A', 'B'）
        track_instruments_dict: 楽器情報を格納する辞書（更新される）
        verbose: デバッグ情報を表示するかどうか
    Returns:
        tuple: (処理済みのデータ, 更新された楽器辞書, 抽出されたテンポ)
    """
    if verbose:
        print(f"DEBUG preprocess_and_extract: Processing track '{track_char}' line data")
        
    # 先頭の空白を削除
    line_content_stripped = line_content.lstrip()
    
    # 1. トラックのテンポ指定（@tXXX）を抽出して削除
    extracted_tempo = None
    
    # 複数のテンポパターンを試みる
    tempo_patterns = [
        r'@t(\d+)',           # 基本的なパターン: @t220
        r'@t\s+(\d+)',        # スペース入りパターン: @t 220
        r'@\s*t\s*(\d+)'      # 任意のスペース: @ t 220
    ]
    
    for pattern in tempo_patterns:
        tempo_match = re.search(pattern, line_content_stripped)
        if tempo_match:
            extracted_tempo = int(tempo_match.group(1))
            if verbose:
                print(f"DEBUG preprocess_and_extract: Found tempo @t{extracted_tempo} in track '{track_char}'")
            
            # マッチした部分を削除
            line_content_stripped = line_content_stripped[:tempo_match.start()] + line_content_stripped[tempo_match.end():]
            line_content_stripped = line_content_stripped.lstrip()
            break
    
    # 2. トラック固有の楽器指定（@NN）を抽出して削除
    instrument_match = re.match(r'@(\d+)', line_content_stripped)
    if instrument_match:
        instrument_id_val = instrument_match.group(1)
        track_instruments_dict[track_char] = f"@{instrument_id_val}"
        if verbose:
            print(f"DEBUG preprocess_and_extract: Found instrument @{instrument_id_val} for track '{track_char}'")
        
        # マッチした部分を削除
        line_content_stripped = line_content_stripped[instrument_match.end():].lstrip()
    
    return line_content_stripped, track_instruments_dict, extracted_tempo

def split_track_data(mml_data, channel_id, max_length=MAX_LINE_LENGTH_MMLE, verbose=False):
    """
    長いMMLデータを複数行に分割します。適切な分割ポイントを見つけて正しいプレフィックスを追加します。
    
    Args:
        mml_data: 分割するMMLデータ文字列
        channel_id: チャンネルID（'1', '2', '3'など）
        max_length: 1行の最大長
        verbose: デバッグ情報を表示するかどうか
    Returns:
        list: プレフィックス付きの分割された行のリスト
    """
    if not mml_data.strip():
        return []
    
    result_lines = []
    remaining_data = mml_data.strip()
    
    while remaining_data:
        if len(remaining_data) <= max_length:
            # 残りのデータが1行に収まる場合
            result_lines.append(f"{channel_id} {remaining_data}")
            break
        
        # 適切な分割ポイントを見つける (ノート、休符、オクターブ記号の前)
        split_index = max_length
        
        # 最大長からさかのぼって適切な分割ポイントを探す
        while split_index > 0:
            # 次の文字が音符/休符/オクターブ記号の場合、ここで分割する
            if split_index < len(remaining_data) and remaining_data[split_index] in 'abcdefgrABCDEFGR<>':
                break
            split_index -= 1
        
        # 適切な分割ポイントが見つからない場合は、最大長で分割
        if split_index <= 0:
            split_index = max_length
        
        # 行を追加し、残りのデータを更新
        result_lines.append(f"{channel_id} {remaining_data[:split_index]}")
        remaining_data = remaining_data[split_index:].strip()
    
    if verbose and len(result_lines) > 1:
        print(f"DEBUG split_track_data: Split track {channel_id} data into {len(result_lines)} lines")
    
    return result_lines

def process_mus_commands(track_data, mml_channel_id, verbose=False, is_pdx_mode=False, current_timebase=48):
    """
    MUSコマンドを処理してNDP互換のMML形式に変換します。
    非互換なコマンドを除去し、ループ表記をNDP形式に変換します。
    
    変換一覧:
    - Dコマンド（デチューン）を削除 - NDPには対応するコマンドがないため
    - pコマンド（パンポット）を削除 - NDPには対応するコマンドがないため
    - Lコマンドを@Lに変換 - NDPのループ書式に合わせる
    - [] 括弧記号を削除 - NDPの@L書式では不要なため
    
    Args:
        track_data: 処理するトラックデータ
        mml_channel_id: MMLチャンネルID
        verbose: デバッグ情報を表示するかどうか
        is_pdx_mode: PDXモードかどうか
        current_timebase: 現在のタイムベース
    Returns:
        str: 変換されたMML形式のトラックデータ
    """
    if verbose:
        print(f"DEBUG process_mus_commands: Processing track data for channel {mml_channel_id}")
    
    # 変換不能なコマンドを削除
    # Dコマンド（デチューン）を削除 - 例: D-4, D4 など
    converted_data = re.sub(r'D[-+]?\d+', '', track_data)
    
    # pコマンド（パンポット）を削除 - 例: p1, p0 など
    converted_data = re.sub(r'p\d+', '', converted_data)
    
    # Lコマンドを@Lに変換 (元の[]の代わり)
    converted_data = re.sub(r'\bL\s+', '@L ', converted_data)
    
    # ]コマンドがあれば、それを削除する
    converted_data = re.sub(r'\]', '', converted_data)
    
    # [コマンドがあれば、それも削除する
    converted_data = re.sub(r'\[', '', converted_data)
    
    # 複数の空白を一つに圧縮
    converted_data = re.sub(r'\s+', ' ', converted_data)
    
    if verbose:
        print(f"DEBUG process_mus_commands: Removed unsupported commands (D, p)")
        print(f"DEBUG process_mus_commands: Converted L commands to @L format")
    
    return converted_data

def convert_mml_file(mus_filepath, conversion_mode="default", note_length_mode="frames", verbose=False):
    """
    MUSファイルをMML形式に変換します。
    
    Args:
        mus_filepath: 入力MUSファイルのパス
        conversion_mode: 変換モード（デフォルトまたはdirect_8track）
        note_length_mode: ノート長モード（framesまたはticks）
        verbose: デバッグ情報を表示するかどうか
    Returns:
        str: 変換されたMML形式の文字列
    """
    # conversion_mode の検証（互換性のために残す）
    if conversion_mode not in ["default", "direct_8track"]:
        print(f"Warning: conversion_mode '{conversion_mode}' might not be fully applicable for MML output.")
    
    try:
        with open(mus_filepath, 'r', encoding='utf-8', errors='replace') as f:
            mus_content = f.read()
    except Exception as e:
        return f"Error reading MUS file: {e}"

    # MUSファイルの内容をパースする
    if verbose:
        print(f"DEBUG convert_mml_file: Parsing MUS file: {mus_filepath}")
    parsed_data = parse_mus_file(mus_content, verbose=verbose)

    title = parsed_data.get('title', "Untitled")
    composer = parsed_data.get('composer', "Unknown")
    mus_tempo = parsed_data.get('mus_tempo')  # 抽出されたMUSテンポ
    
    # タイムベースの設定
    timebase = NDP_TIMEBASE  # デフォルトのタイムベース

    # MML出力の基本構造を作成
    mml_output_parts = [
        f'#TITLE "{title}"',
        f'#COMPOSER "{composer}"',
        f'#TIMEBASE {timebase}',
    ]

    # テンポコマンドの追加（mus_tempoが利用可能な場合）
    # MUSファイルのテンポ情報（@t220など）をNDP MMLのテンポ情報（123 T163など）に変換
    if mus_tempo is not None and 1 <= mus_tempo <= 255:  # テンポが有効範囲内であることを確認
        try:
            # MUSテンポからBPMへの変換式
            # 変換式: bpm = round((60 * 4000000) / (40 * 1024 * (256 - mus_tempo)))
            # 式の意味: MUSのテンポ値は内部木遠数を表すため、BPMに変換する必要がある
            # 例えば、@t220は約163 BPMに相当する
            bpm = round((60 * 4000000) / (40 * 1024 * (256 - mus_tempo)))
            
            # テンポコマンド用のアクティブなNDPトラックを特定
            # NDP MMLでは、テンポコマンドは実行されるトラック番号を指定する必要がある
            # 例: 123 T163 （トラック1、2、3がテンポ163で実行される）
            active_ndp_tracks_for_tempo = []
            
            if parsed_data.get('tracks'):
                # 解析されたMUSファイルから使用中の全トラックを取得
                sorted_mus_keys_for_tempo = sorted(parsed_data['tracks'].keys())
                for mus_key in sorted_mus_keys_for_tempo:
                    # MUSトラック名（A、B、Cなど）をNDPトラック番号（1、2、3など）に変換
                    ndp_track_num = MUS_TO_NDP_TRACK_MAP.get(mus_key.upper())
                    if ndp_track_num:
                        active_ndp_tracks_for_tempo.append(ndp_track_num)
                
                if active_ndp_tracks_for_tempo:
                    # トラック番号を数値順にソートして結合（例: ["1", "2", "3"] -> "123"）
                    active_ndp_tracks_for_tempo.sort(key=int) 
                    tempo_track_prefix = "".join(active_ndp_tracks_for_tempo)
                    # テンポコマンドをMML出力に追加（例: "123 T163"）
                    mml_output_parts.append(f'{tempo_track_prefix} T{bpm}')
                    if verbose:
                        print(f"DEBUG convert_mml_file: Added tempo command: {tempo_track_prefix} T{bpm}")
        except ZeroDivisionError:
            print(f"Warning: MUS tempo {mus_tempo} resulted in division by zero. Tempo command skipped.")
        except Exception as e:
            print(f"Warning: Error calculating BPM from MUS tempo {mus_tempo}: {e}. Tempo command skipped.")

    # ヘッダーの後に空行を追加
    mml_output_parts.append('')  

    # 音色定義の追加（コメントとして）
    if parsed_data.get('voice_definitions'): 
        mml_output_parts.append("// Voice Definitions (from MUS @ NN={...})")
        for voice_id, voice_data_str in sorted(parsed_data['voice_definitions'].items()):
            # 音色データ文字列のクリーンアップ
            voice_comment = str(voice_data_str).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            voice_comment = re.sub(r'\s+', ' ', voice_comment).strip()
            mml_output_parts.append(f"// {voice_id} = {voice_comment}")
        mml_output_parts.append('')  # 音色定義の後に空行
    
    # トラック固有の楽器指定があれば追加
    if parsed_data.get('track_instruments'):
        has_simple_track_instruments = any(val for val in parsed_data['track_instruments'].values())
        if has_simple_track_instruments:
            mml_output_parts.append("// Track-specific Instrument Assignments (from MUS Track @NN)")
            for track_char, inst_id_str in sorted(parsed_data['track_instruments'].items()):
                if inst_id_str:  # 楽器が割り当てられている場合
                     mml_output_parts.append(f"// Track {track_char}: {inst_id_str}")
            mml_output_parts.append('')  # 空行

    # トラックデータの処理
    processed_tracks_output = []
    # 一貫したMML出力順序のためにMUSトラック文字でソート
    sorted_mus_track_keys = sorted(parsed_data.get('tracks', {}).keys())
    
    if verbose:
        print(f"DEBUG convert_mml_file: Processing tracks: {sorted_mus_track_keys}")
    
    for mus_track_key in sorted_mus_track_keys:
        full_mus_track_data = parsed_data['tracks'][mus_track_key]
        mml_channel_id = MUS_TO_NDP_TRACK_MAP.get(mus_track_key.upper())
        
        if not mml_channel_id:
            # MMLチャンネルマッピングがないトラックはスキップ
            if verbose:
                print(f"DEBUG convert_mml_file: Skipping track '{mus_track_key}' (no channel mapping)")
            continue

        processed_tracks_output.append(f"// トラック {mus_track_key.upper()} (チャンネル {mml_channel_id})")
        
        # トラックデータをMML形式に変換
        single_mml_track_string = process_mus_commands(
            full_mus_track_data, 
            mml_channel_id, 
            verbose=verbose, 
            is_pdx_mode=False,
            current_timebase=timebase
        )
        
        # 長いMML文字列を行に分割
        mml_track_lines_split = split_track_data(
            single_mml_track_string, 
            mml_channel_id, 
            max_length=MAX_LINE_LENGTH_MMLE, 
            verbose=verbose
        )
        
        processed_tracks_output.extend(mml_track_lines_split)
        processed_tracks_output.append('')  # 各トラックのMML内容の後に空行を追加
    
    # 最終的なMML出力を構築
    mml_output_parts.extend(processed_tracks_output)
    
    final_mml_content = "\n".join(mml_output_parts).strip()
    # ファイルが空でも末尾に改行を確保
    return final_mml_content + "\n" if final_mml_content else "\n"

def parse_arguments():
    """
    コマンドライン引数を解析します。
    """
    import argparse
    parser = argparse.ArgumentParser(description="MUS形式をMML形式に変換します。")
    
    parser.add_argument('input_file', help="入力MUSファイルのパス")
    parser.add_argument('-o', '--output', help="出力MMLファイルのパス（省略時は入力ファイル名.mml）")
    parser.add_argument('-m', '--mode', choices=["default", "direct_8track"], default="default", help="変換モード")
    parser.add_argument('-l', '--length-mode', choices=["frames", "ticks"], default="frames", help="ノート長の単位")
    parser.add_argument('--octave-offset', type=int, default=0, help="オクターブオフセット（デフォルト: 0）")
    parser.add_argument('-v', '--verbose', action='store_true', help="詳細な出力を表示")
    
    return parser.parse_args()

def main():
    """
    メイン実行関数
    """
    args = parse_arguments()
    
    # 入力ファイルの存在確認
    if not os.path.exists(args.input_file):
        print(f"エラー: 入力ファイルが見つかりません: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    # 出力ファイルパスの決定
    if args.output:
        output_path = args.output
    else:
        # 入力ファイル名の拡張子を.mmlに変更
        file_name, _ = os.path.splitext(args.input_file)
        output_path = f"{file_name}.mml"
    
    if args.verbose:
        print(f"変換中: {args.input_file} -> {output_path}")
        print(f"モード: {args.mode}, ノート長モード: {args.length_mode}")
    
    # オクターブオフセットの設定（グローバル変数）
    global MUS_TO_NDP_OCTAVE_OFFSET
    MUS_TO_NDP_OCTAVE_OFFSET = args.octave_offset
    
    # 出力ディレクトリの確認と作成
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            print(f"エラー: 出力ディレクトリの作成に失敗しました: {e}", file=sys.stderr)
            sys.exit(1)
    
    try:
        # ファイルを変換
        result = convert_mml_file(
            args.input_file,
            conversion_mode=args.mode,
            note_length_mode=args.length_mode,
            verbose=args.verbose
        )
        
        # 結果をファイルに保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        
        if args.verbose:
            print(f"変換が完了しました: {output_path}")
            
    except Exception as e:
        print(f"エラー: 変換中にエラーが発生しました: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
