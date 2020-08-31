

if __name__ == "__main__":
    from octo_tku_upload.digests import TKUEmailDigest

    TKUEmailDigest.upload_daily_fails_warnings(
        day_select=2,
        status='error',
        tku_type='tkn_main_continuous',
        fake_run=True,
    )