Material folder structure:

sp,so,U,J
    named runs

    DOS
    band structure

    batch runs
    k-optimization
    a,b,c optimization
    volume optimization

# init_lapw -m

1. Reduction            (%;                 {ENTER})
2. Scheme               (o/N;               N)
3. Radii                (a/d/r;             a)
    if r: # this is not possible in the init_lapw_Params object
    jump to 1.
4. Near-neighbor        (int;               2)
^X
c
^X
c
^X
c
8. lstart               (-up/-dn/-nm/-ask; -up)
    if -ask:
        N-times:        (u/d/n)
        ...
9. method               (13/5/11/19 aka GGA-PBE/LDA/GGA-WC/GGA_PBESOL;     13)
10. Separation energy   (float;             -6.0)
^X
c
^X
^X
11. k-points            (pos int or -1;     1000)
    if -1:
    12. density         (float; bohr^-1;    0.1)
13. k-shift             (0/1;               0)
^X
c
^X
14. spin polarized      (y/n;               y)
^X
^X
    if y:
    15. antiferromagnetic   (y/n;               y)


# init_so_lapw

1. h, k, l                  (int triplet;   0 0 1)
2. so ignoring atoms        (int array;     none)
3. EMAX                     (float Ryd;     5.0)
4. RLOs                     (N/a/c;         NONE/All/choose)
if c:
    y/n - atom count times
^X
^X
5. is_sp?                   (y/n;           N)
if y:
    ^X
    6. use for SO               (y/n;           y)
    if y:
        7. k-points                 (int;           1000)
        ^X
        8. rerun kgen?              (forced n)

