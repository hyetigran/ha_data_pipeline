# Each visit belongs to one job or estimate

A visit gets its provider and home through its job or estimate.

The program avoids keeping separate copies that could disagree. For example, the visit should not name one business while its job names another.

The current model allows one provider and at most one resolved home for each job or estimate. Work involving several businesses or homes would need an explicit model change.

---

[Start here](../README.md) · [Original document](../../adr/0010-inherit-visit-provider-and-property.md)
