import re
import os
import sys
from mdx_converter_logic import parse_mus_file

def extract_and_convert_tempo(mus_filepath, verbose=True):
    """
    MUSファイルからテンポ情報を抽出し、NDP MMLのBPMに変換します
    
    Args:
        mus_filepath: 入力MUSファイルのパス
        verbose: デバッグ情報を表示するか
    Returns:
        tuple: (mus_tempo, ndp_bpm, active_tracks)
    """
    try:
        with open(mus_filepath, 'r', encoding='utf-8', errors='replace') as f:
            mus_content = f.read()
    except Exception as e:
        print(f"Error reading MUS file: {e}")
        return None, None, []
    
    # MUSファイル内容を解析
    parsed_data = parse_mus_file(mus_content, verbose=verbose)
    
    # MUSテンポを取得
    mus_tempo = parsed_data.get('mus_tempo')
    if verbose:
        print(f"MUS tempo extracted: {mus_tempo}")
    
    # テンポが無効の場合は終了
    if mus_tempo is None or not (1 <= mus_tempo <= 255):
        return mus_tempo, None, []
    
    # MUS tempoからBPMへの変換式
    try:
        bpm = round((60 * 4000000) / (40 * 1024 * (256 - mus_tempo)))
        if verbose:
            print(f"Converted MUS tempo {mus_tempo} to BPM {bpm}")
    except Exception as e:
        print(f"Error converting tempo: {e}")
        return mus_tempo, None, []
    
    # アクティブなトラックを特定
    active_tracks = []
    MUS_TO_NDP_TRACK_MAP = {
        'A': '1', 'B': '2', 'C': '3', 'D': '4',
        'E': '5', 'F': '6', 'G': '7', 'H': '8'
    }
    
    if parsed_data.get('tracks'):
        sorted_tracks = sorted(parsed_data['tracks'].keys())
        for track in sorted_tracks:
            ndp_track = MUS_TO_NDP_TRACK_MAP.get(track.upper())
            if ndp_track:
                active_tracks.append(ndp_track)
    
    return mus_tempo, bpm, active_tracks

def insert_tempo_to_mml(mml_filepath, bpm, active_tracks, verbose=True):
    """
    MMLファイルに計算されたテンポ情報を挿入します
    
    Args:
        mml_filepath: MMLファイルのパス
        bpm: 挿入するBPM値
        active_tracks: アクティブなトラック番号のリスト
        verbose: デバッグ情報を表示するか
    """
    if not bpm or not active_tracks:
        if verbose:
            print("No BPM or active tracks to insert")
        return False
    
    try:
        # MMLファイルを読み込み
        with open(mml_filepath, 'r', encoding='utf-8') as f:
            mml_content = f.read()
        
        # #TIMEBASE行の位置を特定
        timebase_match = re.search(r'(#TIMEBASE\s+\d+)', mml_content)
        if not timebase_match:
            if verbose:
                print("No #TIMEBASE line found in MML file")
            return False
            
        # テンポコマンド文字列を作成
        track_prefix = ''.join(active_tracks)
        tempo_command = f"{track_prefix} T{bpm}"
        
        if verbose:
            print(f"Inserting tempo command: {tempo_command}")
        
        # #TIMEBASE行の後にテンポコマンドを挿入
        timebase_pos = timebase_match.end()
        new_mml_content = mml_content[:timebase_pos] + f"\n{tempo_command}" + mml_content[timebase_pos:]
        
        # 変更内容をファイルに書き込み
        with open(mml_filepath, 'w', encoding='utf-8') as f:
            f.write(new_mml_content)
            
        if verbose:
            print(f"Successfully updated {mml_filepath} with tempo command")
        return True
    
    except Exception as e:
        print(f"Error updating MML file: {e}")
        return False

def main():
    # コマンドライン引数の確認
    if len(sys.argv) < 3:
        print("使用方法: python extract_tempo.py <MUSファイル> <MMLファイル> [--quiet]")
        sys.exit(1)
    
    mus_file = sys.argv[1]
    mml_file = sys.argv[2]
    verbose = "--quiet" not in sys.argv
    
    if not os.path.exists(mus_file):
        print(f"エラー: MUSファイルが見つかりません: {mus_file}")
        sys.exit(1)
    
    if not os.path.exists(mml_file):
        print(f"エラー: MMLファイルが見つかりません: {mml_file}")
        sys.exit(1)
    
    # テンポ抽出と変換
    mus_tempo, bpm, active_tracks = extract_and_convert_tempo(mus_file, verbose)
    
    if mus_tempo is None:
        print("テンポ情報の抽出に失敗しました")
        sys.exit(1)
    
    if bpm is None:
        print(f"MUSテンポ {mus_tempo} からBPMへの変換に失敗しました")
        sys.exit(1)
    
    # テンポコマンドをMMLに挿入
    success = insert_tempo_to_mml(mml_file, bpm, active_tracks, verbose)
    
    if success:
        print(f"テンポコマンドを正常に挿入しました: {active_tracks} T{bpm}")
    else:
        print("テンポコマンドの挿入に失敗しました")
        sys.exit(1)

if __name__ == "__main__":
    main()
