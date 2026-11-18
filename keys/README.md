# keys/

Put your Snowflake private key here as `rsa_key.p8`.

Generate a key pair (unencrypted):

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
chmod 600 rsa_key.p8
```

Register the public key in Snowflake (paste the text between the BEGIN/END lines):

```sql
ALTER USER <your_user> SET RSA_PUBLIC_KEY='MIIBIjANBgkqh...';
DESC USER <your_user>;   -- check RSA_PUBLIC_KEY_FP
```

Never share `rsa_key.p8`. Only the `.pub` file goes to Snowflake.
