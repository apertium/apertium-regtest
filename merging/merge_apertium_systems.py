import os
import shutil
from merge_modes import generate_modes_file
from merge_makefile import merge_makefiles
from merge_json import merge_tests_json
from merge_configure import merge_configure_ac, extract_lang_version_pairs

def merge_directories(eng_deu_dir, spa_cat_dir, unified_models_dir):
    os.makedirs(unified_models_dir, exist_ok=True)

    def copy_files(src_dir, dst_dir):
        for root, _, files in os.walk(src_dir):
            for file in files:
                src_file = os.path.join(root, file)
                relative_path = os.path.relpath(src_file, src_dir)
                dst_file = os.path.join(dst_dir, relative_path)  # Preserve directory structure
                
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                if os.path.exists(src_file) and not os.path.exists(dst_file):
                    shutil.copy(src_file, dst_file)

    copy_files(eng_deu_dir, unified_models_dir)
    copy_files(spa_cat_dir, unified_models_dir)

    generate_modes_file(eng_deu_dir, spa_cat_dir, unified_models_dir)

    makefile_eng_deu_path = os.path.join(eng_deu_dir, "Makefile")
    makefile_spa_cat_path = os.path.join(spa_cat_dir, "Makefile")
    
    if os.path.exists(makefile_eng_deu_path) and os.path.exists(makefile_spa_cat_path):
        output_file = os.path.join(unified_models_dir, "Makefile")
        merge_makefiles(makefile_eng_deu_path, makefile_spa_cat_path, output_file)

    unified_test_dir = os.path.join(unified_models_dir, "test")
    os.makedirs(unified_test_dir, exist_ok=True)
    merge_tests_json(
        output_path=f"{unified_models_dir}/test/tests.json",
        file1_path=f"{eng_deu_dir}/test/tests.json", 
        file2_path=f"{spa_cat_dir}/test/tests.json", 
    )
    configure_ac_eng_deu_path = os.path.join(eng_deu_dir, "configure.ac")
    configure_ac_spa_cat_path = os.path.join(spa_cat_dir, "configure.ac")
    lang_version_pairs = extract_lang_version_pairs(configure_ac_eng_deu_path)
    lang_version_pairs += extract_lang_version_pairs(configure_ac_spa_cat_path)
    merged_configure_ac_content = merge_configure_ac(
        configure_ac_eng_deu_path, configure_ac_spa_cat_path, lang_version_pairs
    )
    with open(os.path.join(unified_models_dir, "configure.ac"), "w") as f:
        f.write(merged_configure_ac_content)

eng_deu_dir = "/home/ash/apertium-regtest/apertium-eng-deu"
spa_cat_dir = "/home/ash/apertium-regtest/apertium-spa-cat"
unified_models_dir = "/home/ash/apertium-regtest/unified-models"

merge_directories(eng_deu_dir, spa_cat_dir, unified_models_dir)
