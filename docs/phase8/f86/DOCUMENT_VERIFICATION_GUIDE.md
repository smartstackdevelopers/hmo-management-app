# Document Verification Guide

`GET /signing-requests/{id}/verify-integrity` compares the stored hash with current `file_metadata.checksum_sha256`.

A match indicates consistency with the recorded hash — not legal tamper-proof status.
