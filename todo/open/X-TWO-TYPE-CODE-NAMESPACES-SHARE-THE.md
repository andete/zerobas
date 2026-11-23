- [ ] 🔴 **Two type-code namespaces share the value `1`** — the published `DEFTBL`
      string code and zerobas's own variable-chain string tag. D-DEFSTR fixed the
      three sites that crossed them (one was a live memory corruption) but the two
      namespaces still overlap on the numeric values, so the next site that feeds
      one into the other reintroduces the class. Collapse to ONE. Detail:
      *“`DEFTBL_STR` SHOULD BE `3`, NOT `1`”*, line 4072.
