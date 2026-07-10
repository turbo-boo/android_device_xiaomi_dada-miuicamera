#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: 2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

import os
import struct
import tempfile
import zipfile

from extract_utils.fixups_blob import (
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.fixups_lib import (
    lib_fixups,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)

namespace_imports = [
    'device/xiaomi/dada-miuicamera',
]


def align_movielens_version(ctx, file, file_path, *args, **kwargs):
    """Make the feature split attach to the OS3.0.6.0 base APK."""
    base_version = 640001302
    split_version = 502309269
    old_value = struct.pack('<I', split_version)
    new_value = struct.pack('<I', base_version)

    with zipfile.ZipFile(file_path, 'r') as source:
        manifest = source.read('AndroidManifest.xml')
        if manifest.count(old_value) != 1:
            raise ValueError('unexpected movielens manifest version layout')

        fd, temporary_path = tempfile.mkstemp(
            prefix='movielens-', suffix='.apk', dir=os.path.dirname(file_path)
        )
        os.close(fd)
        try:
            with zipfile.ZipFile(temporary_path, 'w') as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == 'AndroidManifest.xml':
                        data = data.replace(old_value, new_value, 1)
                    target.writestr(info, data)
            os.replace(temporary_path, file_path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

blob_fixups: blob_fixups_user_type = {
    'system/lib64/libcamera_algoup_jni.xiaomi.so': blob_fixup()
        .add_needed('libgui_shim_miuicamera.so')
        .sig_replace('08 AD 40 F9', '08 A9 40 F9'),
    'system/lib64/libcamera_mianode_jni.xiaomi.so': blob_fixup()
        .add_needed('libgui_shim_miuicamera.so'),
    'system/lib64/libmicampostproc_client.so': blob_fixup()
        .remove_needed('libhidltransport.so'),
    'system/priv-app/MiuiCamera/MiuiCamera.apk': blob_fixup()
        .apktool_patch('patches'),
    'system/priv-app/MiuiCamera/split_movielens.apk': blob_fixup().call(
        align_movielens_version,
        need_tmp_dir=False,
    ),
}  # fmt: skip

module = ExtractUtilsModule(
    'dada-miuicamera',
    'xiaomi',
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
)

if __name__ == '__main__':
    utils = ExtractUtils.device(module)
    utils.run()
