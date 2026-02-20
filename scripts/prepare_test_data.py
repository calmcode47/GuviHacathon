import os
import shutil
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path

# Paths to unseen human samples identified via PowerShell
HUMAN_SAMPLES = {
    "english": [
        "N:/speech data/human/english/english_human_som_09799_02066909888_001.wav",
        "N:/speech data/human/english/english_human_som_09799_02086878939_000.wav",
        "N:/speech data/human/english/english_human_som_09799_02086878939_001.wav",
        "N:/speech data/human/english/english_human_som_09799_02087770255_000.wav",
        "N:/speech data/human/english/english_human_som_09799_02101671499_000.wav",
        "N:/speech data/human/english/english_human_som_09799_02101671499_001.wav",
        "N:/speech data/human/english/english_human_som_09799_02101771330_000.wav",
        "N:/speech data/human/english/english_human_som_09799_02106411805_000.wav",
        "N:/speech data/human/english/english_human_som_09799_02116778541_000.wav",
        "N:/speech data/human/english/english_human_som_09799_02127712914_000.wav"
    ],
    "hindi": [
        "N:/speech data/human/hindi/hindi_human_839-3977374_001.wav",
        "N:/speech data/human/hindi/hindi_human_839-3977374_002.wav",
        "N:/speech data/human/hindi/hindi_human_839-3977374_003.wav",
        "N:/speech data/human/hindi/hindi_human_839-3977374_004.wav",
        "N:/speech data/human/hindi/hindi_human_839-3977374_005.wav",
        "N:/speech data/human/hindi/hindi_human_839-3977374_006.wav",
        "N:/speech data/human/hindi/hindi_human_839-3977374_007.wav",
        "N:/speech data/human/hindi/hindi_human_839-3977374_008.wav",
        "N:/speech data/human/hindi/hindi_human_839-3977374_009.wav",
        "N:/speech data/human/hindi/hindi_human_839-3977374_010.wav"
    ],
    "malayalam": [
        "N:/speech data/human/malayalam/malayalam_human_mlm_09171_01935841379_000.wav",
        "N:/speech data/human/malayalam/malayalam_human_mlm_09171_01966610312_000.wav",
        "N:/speech data/human/malayalam/malayalam_human_mlm_09171_01979980882_000.wav",
        "N:/speech data/human/malayalam/malayalam_human_mlm_09171_01981461747_000.wav",
        "N:/speech data/human/malayalam/malayalam_human_mlm_09171_02071466917_000.wav",
        "N:/speech data/human/malayalam/malayalam_human_mlm_09171_02101052319_000.wav",
        "N:/speech data/human/malayalam/malayalam_human_mlm_09171_02121904204_000.wav",
        "N:/speech data/human/malayalam/malayalam_human_mlm_09171_02122542278_000.wav",
        "N:/speech data/human/malayalam/malayalam_human_mlm_09171_02136277993_000.wav",
        "N:/speech data/human/malayalam/malayalam_human_mlm_09171_02138515864_000.wav"
    ],
    "tamil": [
        "N:/speech data/human/tamil/tamil_human_tag_09674_01922074735_000.wav",
        "N:/speech data/human/tamil/tamil_human_tag_09674_02032096732_000.wav",
        "N:/speech data/human/tamil/tamil_human_tag_09674_02037054574_000.wav",
        "N:/speech data/human/tamil/tamil_human_tag_09674_02133733019_000.wav",
        "N:/speech data/human/tamil/tamil_human_tag_09674_02145728180_000.wav",
        "N:/speech data/human/tamil/tamil_human_tag_09720_00747403932_000.wav",
        "N:/speech data/human/tamil/tamil_human_tag_09720_00796189657_000.wav",
        "N:/speech data/human/tamil/tamil_human_tag_09720_01045724790_000.wav",
        "N:/speech data/human/tamil/tamil_human_tag_09720_01854560946_000.wav",
        "N:/speech data/human/tamil/tamil_human_tag_09720_01880142942_000.wav"
    ],
    "telugu": [
        "N:/speech data/human/telugu/telugu_human_tem_09584_01039036255_000.wav",
        "N:/speech data/human/telugu/telugu_human_tem_09584_01048486662_000.wav",
        "N:/speech data/human/telugu/telugu_human_tem_09584_01162477807_000.wav",
        "N:/speech data/human/telugu/telugu_human_tem_09584_01276424775_000.wav",
        "N:/speech data/human/telugu/telugu_human_tem_09584_01344530762_000.wav",
        "N:/speech data/human/telugu/telugu_human_tem_09584_01358102467_000.wav",
        "N:/speech data/human/telugu/telugu_human_tem_09584_01390657811_000.wav",
        "N:/speech data/human/telugu/telugu_human_tem_09584_01489049719_000.wav",
        "N:/speech data/human/telugu/telugu_human_tem_09584_01629319103_000.wav",
        "N:/speech data/human/telugu/telugu_human_tem_09584_02047229027_000.wav"
    ]
}

def prepare_data():
    base_out = Path("N:/speech data/test_data/human")
    edge_out = Path("N:/speech data/test_data/edge_cases")
    os.makedirs(base_out, exist_ok=True)
    os.makedirs(edge_out, exist_ok=True)

    for lang, paths in HUMAN_SAMPLES.items():
        lang_dir = base_out / lang
        os.makedirs(lang_dir, exist_ok=True)
        for i, src in enumerate(paths):
            dst = lang_dir / f"{lang}_test_human_{i:03d}.wav"
            shutil.copy(src, dst)
            print(f"Copied {src} to {dst}")

    # Synthesize Edge Cases
    # Pick one human sample as base for edge cases
    base_sample_path = HUMAN_SAMPLES["english"][0]
    y, sr = librosa.load(base_sample_path, sr=16000)

    # 1. Very short clip (< 2s)
    short_y = y[:int(0.8 * sr)] # 0.8 seconds
    sf.write(edge_out / "edge_human_short.wav", short_y, sr)
    print("Generated short clip")

    # 2. Noisy human voice
    noise = np.random.normal(0, 0.05, len(y))
    noisy_y = y + noise
    sf.write(edge_out / "edge_human_noisy.wav", noisy_y, sr)
    print("Generated noisy clip")

    # 3. Phone quality (low bitrate / narrowband)
    # Simple way is to resample down and up, and maybe filter
    # But just resampling to 8k and back to 16k mimics the frequency cutoff
    y_8k = librosa.resample(y, orig_sr=sr, target_sr=8000)
    y_phone = librosa.resample(y_8k, orig_sr=8000, target_sr=16000)
    sf.write(edge_out / "edge_human_phone.wav", y_phone, sr)
    print("Generated phone quality clip")

    # For AI advanced, it's already generated via edge-tts in the main test set.
    # We can also generate a specific "neural" one if we want.

if __name__ == "__main__":
    prepare_data()
