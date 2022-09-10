Examples
========


A simple C case
---------------

Make sure you have a *ccrawlrc* file as shown in Installation_, (or remove `-c ccrawlrc`
in commands below.)
In a terminal, open file "ccrawl/tests/samples/header.h".
Open another terminal and within your virtualenv do::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test1.db collect ~/ccrawl/tests/samples
  [ 50%] /home/user/ccrawl/tests/samples/header.h                                                [ 23]
  [100%] /home/user/ccrawl/tests/samples/xxx/yyy/somewhere.h                                     [  9]
  ----------------------------------------------------------------------------------------------------
  saving database...                                                                             [ 32]


ccrawl has now collected all "\*.h" files in the samples/ directory.

Let us search for all objects with symbol containing "MY"::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test1.db search "MY"
  found cMacro identifer "MYSTRING"
  found cMacro identifer "MYEXPR"
  found cMacro identifer "MYMACRO"
  found cMacro identifer "MYCONST"

Search for all typedefs currently in the test1.db local database::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test1.db select -a "cls=cTypedef"
  found cTypedef identifer "foo1"
  found cTypedef identifer "__u8"
  found cTypedef identifer "myunion"
  found cTypedef identifer "myinteger"
  found cTypedef identifer "foo"
  found cTypedef identifer "foo2"
  found cTypedef identifer "unspelled"
  found cTypedef identifer "myu8"
  found cTypedef identifer "mystruct"
  found cTypedef identifer "tags"
  found cTypedef identifer "xxx"
  found cTypedef identifer "pac3"
  found cTypedef identifer "p_unspelled"


Search for all functions prototypes that return a myunion type and have a mystruct type as 2d arg::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test1.db select prototype 0:myunion 2:mystruct
  myunion myFunc(p_unspelled, mystruct);

Search all constants with value 0x10::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test1.db select constant 0x10
  MYCONST

Print type "foo2" in C language as then as python ctypes::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test1.db show -r foo2
  typedef void *(*(*foo2[2])(int, void **))[3];

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test1.db show -f ctypes -r foo2
  foo2 = CFUNCTYPE(POINTER(c_void_p*3), c_int, c_void_p)*2


Print type "p_unspelled" (without and then with recurssion) in C::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test1.db show p_unspelled
  typedef struct unspelled *p_unspelled;

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test1.db show -r p_unspelled
  enum X {
    X_0 = 0,
    X_1 = 1,
    X_2 = 2,
    X_3 = 3
  }

  struct _bar {
    enum X x;
  }
  typedef int (*foo)(int, int, int);
  struct _mystruct;
  typedef unsigned char xxx;
  typedef xxx myinteger;

  struct _mystruct {
    myinteger I;
    int tab[12];
    unsigned char p[16];
    short *s;
    struct _mystruct *next;
    foo func;
    struct _bar bar[2];
  }

  struct unspelled {
    char *c[4];
    void (*func[2])(myinteger, foo, struct _mystruct *);
    struct _mystruct stab[18];
    int *x;
    unsigned long long y;
    char (*PtrCharArrayOf3[2])[3];
    union  {
      unsigned int A;
      myinteger *myi;
      short w[2];
    } sAB;
  }
  typedef struct unspelled *p_unspelled;


Print type "struct _mystruct" (without recurssion) in ctypes format::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test1.db show -f ctypes 'struct _mystruct'
  struct__mystruct = type('struct__mystruct',(Structure,),{})

  struct__mystruct._fields_ = [("I", myinteger),
                               ("tab", c_int*12),
                               ("p", c_ubyte*16),
                               ("s", POINTER(c_short)),
                               ("next", POINTER(struct__mystruct)),
                               ("func", foo),
                               ("bar", struct__bar*2)]


Select data structures with a type of length 8 at offset 88 (bytes)::

  (venv) user@machine:/tmp % ccrawl -l test1.db find struct "88:+8"
  struct _mystruct {
    myinteger I;
    int tab[12];
    unsigned char p[16];
    short *s;
    struct _mystruct *next;
    foo func;
    struct _bar bar[2];
  }
  identifier __u16 not found
  identifier __u16 not found
  identifier struct ts_config not found
  can't build struct xt_string_info..skipping.


A more realistic case
---------------------

We collect all definitions from */usr/include/openssl* ::

  (venv) user@machine:/tmp % time ccrawl -l test2.db collect /usr/include/openssl
  [  1%] /usr/include/openssl/crypto.h                                               [3400]
  [  9%] /usr/include/openssl/rc2.h                                                   [ 15]
  [ 11%] /usr/include/openssl/modes.h                                                 [ 45]
  [ 12%] /usr/include/openssl/symhacks.h                                              [  9]
  [ 13%] /usr/include/openssl/rc4.h                                                   [  9]
  [ 15%] /usr/include/openssl/ecdh.h                                                 [5383]
  [ 22%] /usr/include/openssl/err.h                                                  [4188]
  [ 25%] /usr/include/openssl/camellia.h                                              [ 20]
  [ 26%] /usr/include/openssl/md5.h                                                   [ 20]
  [ 27%] /usr/include/openssl/pem2.h                                                  [  1]
  [ 29%] /usr/include/openssl/sha.h                                                   [ 57]
  [ 30%] /usr/include/openssl/pkcs7.h                                                [5268]
  [ 31%] /usr/include/openssl/ocsp.h                                                [12040]
  [ 50%] /usr/include/openssl/cms.h                                                 [11445]
  [ 51%] /usr/include/openssl/cmac.h                                                 [8949]
  [ 52%] /usr/include/openssl/md4.h                                                   [ 20]
  [ 54%] /usr/include/openssl/ssl23.h                                                 [  6]
  [ 55%] /usr/include/openssl/tls1.h                                                  [828]
  [ 56%] /usr/include/openssl/pkcs12.h                                              [11278]
  [ 58%] /usr/include/openssl/whrlpool.h                                              [ 20]
  [ 59%] /usr/include/openssl/asn1_mac.h                                             [5094]
  [ 61%] /usr/include/openssl/ssl3.h                                                [13786]
  [ 73%] /usr/include/openssl/kssl.h                                                  [  1]
  [ 75%] /usr/include/openssl/seed.h                                                 [3411]
  [ 76%] /usr/include/openssl/txt_db.h                                               [3895]
  [ 77%] /usr/include/openssl/engine.h                                              [11832]
  [ 81%] /usr/include/openssl/krb5_asn.h                                             [2390]
  [ 83%] /usr/include/openssl/cast.h                                                  [ 15]
  [ 84%] /usr/include/openssl/des.h                                                  [3649]
  [ 88%] /usr/include/openssl/ts.h                                                  [12079]
  [ 90%] /usr/include/openssl/ebcdic.h                                                [353]
  [ 91%] /usr/include/openssl/aes.h                                                   [ 25]
  [ 93%] /usr/include/openssl/conf_api.h                                             [3990]
  [ 94%] /usr/include/openssl/blowfish.h                                              [ 24]
  [ 95%] /usr/include/openssl/srp.h                                                  [3870]
  [ 97%] /usr/include/openssl/dso.h                                                  [3509]
  [ 98%] /usr/include/openssl/ripemd.h                                                [ 20]
  [100%] /usr/include/openssl/asn1t.h                                                [5185]
  ----------------------------------------------------------------------------------------
  saving database...                                                                [17065]
  ccrawl -c ccrawlrc -l test2.db collect /usr/include/openssl  44,55s user 0,48s system
  99% cpu 45,435 total

List all identifiers of type cStruct ::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test2.db select -a cls=cStruct
  found cStruct identifer "struct ?_02144907"
  found cStruct identifer "struct ASN1_AUX_st"
  found cStruct identifer "struct err_state_st"
  found cStruct identifer "struct bn_recp_ctx_st"
  found cStruct identifer "struct hm_header_st"
  found cStruct identifer "struct stack_st_ACCESS_DESCRIPTION"
  found cStruct identifer "struct stack_st_ESS_CERT_ID"
  found cStruct identifer "struct x509_file_st"
  [...]
  found cStruct identifer "struct pem_recip_st"
  found cStruct identifer "struct ?_4dd5ee76"
  found cStruct identifer "struct NETSCAPE_X509_st"

Search for all definitions matching a regular expression ::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test2.db search '.*AUTHORITY_KEYID.*'
  found cMacro identifer "X509V3_F_V2I_AUTHORITY_KEYID"
  found cStruct identifer "struct X509_crl_st" with matching value
  found cFunc identifer "X509_check_akid" with matching value
  found cFunc identifer "AUTHORITY_KEYID_new" with matching value
  found cFunc identifer "i2d_AUTHORITY_KEYID" with matching value
  found cTypedef identifer "AUTHORITY_KEYID" with matching value
  found cStruct identifer "struct x509_st" with matching value
  found cFunc identifer "AUTHORITY_KEYID_free" with matching value
  found cStruct identifer "struct AUTHORITY_KEYID_st"
  found cFunc identifer "d2i_AUTHORITY_KEYID" with matching value

Let's focus on the definition of 'struct x509_st' ::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test2.db show 'struct x509_st'
  struct x509_st {
    X509_CINF *cert_info;
    X509_ALGOR *sig_alg;
    ASN1_BIT_STRING *signature;
    int valid;
    int references;
    char *name;
    CRYPTO_EX_DATA ex_data;
    long ex_pathlen;
    long ex_pcpathlen;
    unsigned long ex_flags;
    unsigned long ex_kusage;
    unsigned long ex_xkusage;
    unsigned long ex_nscert;
    ASN1_OCTET_STRING *skid;
    AUTHORITY_KEYID *akid;
    X509_POLICY_CACHE *policy_cache;
    struct stack_st_DIST_POINT *crldp;
    struct stack_st_GENERAL_NAME *altname;
    NAME_CONSTRAINTS *nc;
    unsigned char sha1_hash[20];
    X509_CERT_AUX *aux;
  }

The recursive output of this structure takes approx. 30s to complete,
with alerts (in red) about missing definition for various types.

It is also possible to spawn an interactive console with ccrawl
loaded and configured. For example lets find all prototypes with
return type 'int' and first argument pointer-to 'EC_KEY' ::

  (venv) user@machine:/tmp % ccrawl -c ccrawlrc -l test2.db

                               _ 
    ___ ___ _ __ __ ___      _| |
   / __/ __| '__/ _` \ \ /\ / / |
  | (_| (__| | | (_| |\ V  V /| |
   \___\___|_|  \__,_| \_/\_/ |_| v1.8.0


  In [1]: ctx.invoke(prototype,proto=("0:int","1:EC_KEY *"))

  int ECDH_set_ex_data(EC_KEY *, int, void *);
  int EC_KEY_set_public_key(EC_KEY *, const EC_POINT *);
  int EC_KEY_precompute_mult(EC_KEY *, BN_CTX *);
  int ECDSA_set_method(EC_KEY *, const ECDSA_METHOD *);
  int i2d_ECParameters(EC_KEY *, unsigned char **);
  int EC_KEY_set_private_key(EC_KEY *, const BIGNUM *);
  int EC_KEY_generate_key(EC_KEY *);
  int ECDSA_set_ex_data(EC_KEY *, int, void *);
  int i2d_ECPrivateKey(EC_KEY *, unsigned char **);
  int EC_KEY_set_public_key_affine_coordinates(EC_KEY *, BIGNUM *, BIGNUM *);
  int i2o_ECPublicKey(EC_KEY *, unsigned char **);
  int EC_KEY_up_ref(EC_KEY *);
  int ECDSA_sign_setup(EC_KEY *, BN_CTX *, BIGNUM **, BIGNUM **);
  int ECDH_set_method(EC_KEY *, const ECDH_METHOD *);
  int i2d_EC_PUBKEY(EC_KEY *, unsigned char **);
  int EC_KEY_set_group(EC_KEY *, const EC_GROUP *);


Et voilà.
