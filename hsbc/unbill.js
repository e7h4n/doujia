(window["webpackJsonp"] = window["webpackJsonp"] || []).push([
  ["unbill"],
  {
    "2c59": function (t, e, n) {
      "use strict";
      n.r(e);
      var r = function () {
          var t = this,
            e = t.$createElement,
            n = t._self._c || e;
          return n(
            "div",
            {
              staticClass: "unbill",
              on: {
                touchstart: t.touchstart,
                touchmove: t.touchmove,
              },
            },
            [
              n(
                "div",
                {
                  staticClass: "unbill-top",
                },
                [
                  n(
                    "div",
                    {
                      staticClass: "bill-head",
                    },
                    [t._v("账单日期" + t._s(t.unBillInfo.billEndDate))]
                  ),
                  t.isAmount
                    ? n(
                        "div",
                        {
                          staticClass: "bill-amount",
                        },
                        [
                          n(
                            "div",
                            {
                              staticClass: "title",
                            },
                            [t._v("未出账单金额")]
                          ),
                          n(
                            "div",
                            {
                              staticClass: "amount-cny",
                            },
                            [
                              t._v(
                                "CNY " +
                                  t._s(
                                    t.unBillInfo.addAllAmtRmb &&
                                      t.unBillInfo.addAllAmtRmb.substring(1)
                                  )
                              ),
                            ]
                          ),
                          t.usdFlag
                            ? n(
                                "div",
                                {
                                  staticClass: "amount-usd",
                                },
                                [
                                  t._v(
                                    "USD " +
                                      t._s(
                                        t.unBillInfo.addAllAmtDol &&
                                          t.unBillInfo.addAllAmtDol.substring(1)
                                      )
                                  ),
                                ]
                              )
                            : t._e(),
                        ]
                      )
                    : t._e(),
                ]
              ),
              n(
                "div",
                {
                  staticClass: "bill-arrow",
                  on: {
                    click: t.showAmount,
                  },
                },
                [
                  n("div", {
                    staticClass: "arrow",
                    class: t.isAmount ? "reverse-arrow" : "",
                  }),
                ]
              ),
              n(
                "div",
                {
                  staticClass: "unbill-middle",
                },
                [
                  n(
                    "div",
                    {
                      staticClass: "unbill-content",
                    },
                    [
                      n(
                        "div",
                        {
                          staticClass: "content-title",
                        },
                        [
                          n("div", [t._v("交易明细")]),
                          n(
                            "div",
                            {
                              staticClass: "unbill-tab",
                            },
                            t._l(t.currencyMap, function (e, r) {
                              return n(
                                "div",
                                {
                                  key: r,
                                  class: t.tabIndex === r ? "select-tab" : "",
                                  on: {
                                    click: function (n) {
                                      return t.onClickTab(e, r);
                                    },
                                  },
                                },
                                [t._v(" " + t._s(e.value) + " ")]
                              );
                            }),
                            0
                          ),
                        ]
                      ),
                      0 === t.billItemList.length
                        ? n(
                            "div",
                            {
                              staticClass: "content-tip",
                            },
                            [
                              n(
                                "div",
                                {
                                  staticClass: "tip-icon",
                                },
                                [t._v("i")]
                              ),
                              n(
                                "div",
                                {
                                  staticClass: "tip-text",
                                },
                                [t._v(" " + t._s(t.tipText) + " ")]
                              ),
                            ]
                          )
                        : t._e(),
                      n(
                        "div",
                        {
                          staticClass: "unbill-item",
                        },
                        t._l(
                          t.billItemList.slice(0, t.billSliceIndex),
                          function (e, r) {
                            return n(
                              "div",
                              {
                                key: r,
                                staticClass: "unbill-list",
                                on: {
                                  click: function (n) {
                                    return t.transactionDetails(e);
                                  },
                                },
                              },
                              [
                                n(
                                  "div",
                                  {
                                    staticClass: "list-left",
                                  },
                                  [
                                    n(
                                      "div",
                                      {
                                        staticClass: "consumption",
                                      },
                                      [
                                        n(
                                          "span",
                                          {
                                            staticClass: "trans-text",
                                          },
                                          [t._v(t._s(e.transDesc))]
                                        ),
                                        n(
                                          "span",
                                          {
                                            class: {
                                              "green-color":
                                                Number(e.transAmount) < 0,
                                            },
                                          },
                                          [t._v(t._s(e.amount))]
                                        ),
                                      ]
                                    ),
                                    n(
                                      "div",
                                      {
                                        staticClass: "card-info",
                                      },
                                      [
                                        n("span", [t._v(t._s(e.date))]),
                                        n("span", [
                                          t._v("卡号末四位" + t._s(e.cardEnd)),
                                        ]),
                                      ]
                                    ),
                                  ]
                                ),
                                n("div", {
                                  staticClass: "list-right",
                                }),
                              ]
                            );
                          }
                        ),
                        0
                      ),
                    ]
                  ),
                  t.billItemList.length
                    ? n(
                        "div",
                        {
                          staticClass: "loading-text",
                        },
                        [t._v(t._s(t.loadingText))]
                      )
                    : t._e(),
                ]
              ),
            ]
          );
        },
        i = [],
        a = n("1da1"),
        s = n("5530"),
        u = n("d4ec"),
        c = n("bee2"),
        l = n("262e"),
        o = n("2caf"),
        d = (n("96cf"), n("4de4"), n("d81d"), n("1276"), n("ac1f"), n("9ab4")),
        h = n("1b40"),
        b = n("d861"),
        p = n("5896"),
        v = n("aa7a"),
        f = n("4bb5"),
        m = n("b225"),
        g = (function (t) {
          Object(l["a"])(n, t);
          var e = Object(o["a"])(n);
          function n() {
            var t;
            return (
              Object(u["a"])(this, n),
              (t = e.apply(this, arguments)),
              (t.isAmount = !0),
              (t.tabIndex = 0),
              (t.billSliceMap = {
                size: 5,
                index: 1,
              }),
              (t.unBillInfo = []),
              (t.currencyMap = [
                {
                  value: "人民币",
                  id: "CNY",
                },
              ]),
              (t.usdFlag = !1),
              (t.timer = null),
              (t.startY = 0),
              (t.moveY = 0),
              (t.newSymbol = "ALL"),
              (t.rmbTipText = "暂无交易记录。"),
              (t.dollarTipText =
                "暂无交易记录。若您已开通外币消费人民币入账设置，您的外币交易已记入人民币账单，请在人民币账单中查询相关交易明细。"),
              t
            );
          }
          return (
            Object(c["a"])(n, [
              {
                key: "tipText",
                get: function () {
                  var t = this.rmbTipText,
                    e = this.dollarTipText,
                    n = this.tabIndex;
                  return 0 === n || 1 === n ? t : e;
                },
              },
              {
                key: "billSliceIndex",
                get: function () {
                  var t = this.billSliceMap,
                    e = t.index,
                    n = t.size;
                  return Object(b["b"])(n, e);
                },
              },
              {
                key: "isTouch",
                get: function () {
                  var t = this.billSliceIndex,
                    e = this.billItemList;
                  return e.length > 5 && t < e.length;
                },
              },
              {
                key: "billItemList",
                get: function () {
                  var t = this.unBillInfo.transList,
                    e = void 0 === t ? [] : t,
                    n = this.newSymbol,
                    r = e.filter(function (t) {
                      var e = t.currency.symbol || "CNY";
                      return "ALL" === n || n === e;
                    });
                  return r.map(function (t) {
                    var e = t.currency,
                      n = t.recordDate,
                      r = (e.mark || "￥") + t.transAmount,
                      i =
                        n.substring(0, 4) +
                        "年" +
                        n.substring(4, 6) +
                        "月" +
                        n.substring(6, 8) +
                        "日",
                      a = e.symbol || "CNY";
                    return Object(s["a"])(
                      {
                        amount: r,
                        date: i,
                        symbol: a,
                      },
                      t
                    );
                  });
                },
              },
              {
                key: "loadingText",
                get: function () {
                  return this.isTouch ? "上滑加载更多..." : "没有更多信息了";
                },
              },
              {
                key: "created",
                value: function () {
                  this.getUnbillInfo();
                },
              },
              {
                key: "getUnbillInfo",
                value: (function () {
                  var t = Object(a["a"])(
                    regeneratorRuntime.mark(function t() {
                      var e, n, r, i, a, s, u, c, l, o;
                      return regeneratorRuntime.wrap(
                        function (t) {
                          while (1)
                            switch ((t.prev = t.next)) {
                              case 0:
                                return (
                                  (e = {
                                    billOption: "A",
                                  }),
                                  this.setLoading({
                                    loading: !0,
                                  }),
                                  (n = Object(v["d"])()),
                                  (t.next = 5),
                                  Object(p["d"])(Object(v["c"])(n, e))
                                );
                              case 5:
                                if (
                                  ((r = t.sent),
                                  this.setLoading({
                                    loading: !1,
                                  }),
                                  r && r.data)
                                ) {
                                  t.next = 10;
                                  break;
                                }
                                return (
                                  this.showErrorDialog({
                                    tip: this.timeoutMsg,
                                  }),
                                  t.abrupt("return")
                                );
                              case 10:
                                if ("0" === r.data.rspCode) {
                                  t.next = 13;
                                  break;
                                }
                                return (
                                  this.showErrorDialog({
                                    tip: r.data.msg,
                                  }),
                                  t.abrupt("return")
                                );
                              case 13:
                                if (
                                  ((i = Object(v["a"])(n, r.data.rspData)),
                                  (i = JSON.parse(i || "{}")),
                                  (a = i),
                                  (s = a.code),
                                  (u = a.msg),
                                  (c = a.rspData),
                                  "000000" === s)
                                ) {
                                  t.next = 20;
                                  break;
                                }
                                return (
                                  sessionStorage.setItem(
                                    "BANK".concat(this.bankCode, "_RES_MAP"),
                                    JSON.stringify({
                                      icon: "fail",
                                      title: "未出账单",
                                      msg: "当前页面禁止访问",
                                      tip: u,
                                      isShowBackBtn: !0,
                                      tipStyle: !0,
                                    })
                                  ),
                                  this.$router.push(m["a"].TIPS),
                                  t.abrupt("return")
                                );
                              case 20:
                                this.checkUsdCard(),
                                  (l = c.billEndDate),
                                  (o = l.split("/")),
                                  (c.billEndDate = o[0] + "月" + o[1] + "日"),
                                  (this.unBillInfo = c);
                              case 25:
                              case "end":
                                return t.stop();
                            }
                        },
                        t,
                        this
                      );
                    })
                  );
                  function e() {
                    return t.apply(this, arguments);
                  }
                  return e;
                })(),
              },
              {
                key: "checkUsdCard",
                value: (function () {
                  var t = Object(a["a"])(
                    regeneratorRuntime.mark(function t() {
                      var e, n, r, i, a, s, u;
                      return regeneratorRuntime.wrap(
                        function (t) {
                          while (1)
                            switch ((t.prev = t.next)) {
                              case 0:
                                return (
                                  (e = {
                                    noUnpackFlag: "1",
                                  }),
                                  this.setLoading({
                                    loading: !0,
                                  }),
                                  (n = Object(v["d"])()),
                                  (t.next = 5),
                                  Object(p["e"])(Object(v["c"])(n, e))
                                );
                              case 5:
                                if (
                                  ((r = t.sent),
                                  this.setLoading({
                                    loading: !1,
                                  }),
                                  r && r.data)
                                ) {
                                  t.next = 10;
                                  break;
                                }
                                return (
                                  this.showErrorDialog({
                                    tip: this.timeoutMsg,
                                  }),
                                  t.abrupt("return")
                                );
                              case 10:
                                if ("0" === r.data.rspCode) {
                                  t.next = 13;
                                  break;
                                }
                                return (
                                  this.showErrorDialog({
                                    tip: r.data.msg,
                                  }),
                                  t.abrupt("return")
                                );
                              case 13:
                                if (
                                  ((i = r.data.rspData),
                                  (a = i.code),
                                  (s = i.msg),
                                  (u = i.rspData),
                                  "000000" === a)
                                ) {
                                  t.next = 18;
                                  break;
                                }
                                return (
                                  this.showErrorDialog({
                                    tip: s,
                                  }),
                                  t.abrupt("return")
                                );
                              case 18:
                                if (
                                  ((this.usdFlag = "true" === u.usdFlag),
                                  !this.usdFlag)
                                ) {
                                  t.next = 22;
                                  break;
                                }
                                return (
                                  (this.currencyMap = [
                                    {
                                      value: "全部",
                                      id: "ALL",
                                    },
                                    {
                                      value: "人民币",
                                      id: "CNY",
                                    },
                                    {
                                      value: "美元",
                                      id: "USD",
                                    },
                                  ]),
                                  t.abrupt("return")
                                );
                              case 22:
                                this.currencyMap = [
                                  {
                                    value: "人民币",
                                    id: "CNY",
                                  },
                                ];
                              case 23:
                              case "end":
                                return t.stop();
                            }
                        },
                        t,
                        this
                      );
                    })
                  );
                  function e() {
                    return t.apply(this, arguments);
                  }
                  return e;
                })(),
              },
              {
                key: "transactionDetails",
                value: function (t) {
                  sessionStorage.setItem(
                    "".concat(this.bankCode, "details"),
                    JSON.stringify(t)
                  ),
                    this.$router.push(m["a"].TRANSACTION_DETAILS);
                },
              },
              {
                key: "touchstart",
                value: function (t) {
                  this.startY = t.touches[0].clientY;
                },
              },
              {
                key: "touchmove",
                value: function (t) {
                  var e = this;
                  this.timer ||
                    (this.timer = setTimeout(function () {
                      (e.moveY = t.touches[0].clientY), e.onTouchEnd();
                    }, 200));
                },
              },
              {
                key: "onTouchEnd",
                value: function () {
                  var t = Object(b["a"])(this.startY, -this.moveY);
                  t > 10 &&
                    this.isTouch &&
                    ((this.billSliceMap.index = 999),
                    (this.moveY = 0),
                    (this.startY = 0),
                    clearTimeout(this.timer),
                    (this.timer = null));
                },
              },
              {
                key: "onClickTab",
                value: function (t, e) {
                  this.tabIndex !== e &&
                    ((this.newSymbol = t.id), (this.tabIndex = e));
                },
              },
              {
                key: "showAmount",
                value: function () {
                  this.isAmount = !this.isAmount;
                },
              },
            ]),
            n
          );
        })(h["c"]);
      Object(d["a"])([f["a"]], g.prototype, "setLoading", void 0),
        Object(d["a"])([f["a"]], g.prototype, "showErrorDialog", void 0),
        (g = Object(d["a"])([h["a"]], g));
      var x = g,
        w = x,
        k = (n("5480"), n("2877")),
        y = Object(k["a"])(w, r, i, !1, null, null, null);
      e["default"] = y.exports;
    },
    5480: function (t, e, n) {
      "use strict";
      n("64a2");
    },
    5896: function (t, e, n) {
      "use strict";
      n.d(e, "a", function () {
        return a;
      }),
        n.d(e, "c", function () {
          return s;
        }),
        n.d(e, "b", function () {
          return u;
        }),
        n.d(e, "d", function () {
          return c;
        }),
        n.d(e, "e", function () {
          return l;
        });
      var r = n("1da1"),
        i = (n("96cf"), n("2600")),
        a = (function () {
          var t = Object(r["a"])(
            regeneratorRuntime.mark(function t(e) {
              return regeneratorRuntime.wrap(
                function (t) {
                  while (1)
                    switch ((t.prev = t.next)) {
                      case 0:
                        return (
                          (t.prev = 0),
                          (t.next = 3),
                          Object(i["a"])({
                            url: "/nwxhf/bill/getCurrentBill",
                            method: "post",
                            data: e,
                          })
                        );
                      case 3:
                        return t.abrupt("return", t.sent);
                      case 6:
                        (t.prev = 6),
                          (t.t0 = t["catch"](0)),
                          console.error(t.t0);
                      case 9:
                      case "end":
                        return t.stop();
                    }
                },
                t,
                null,
                [[0, 6]]
              );
            })
          );
          return function (e) {
            return t.apply(this, arguments);
          };
        })(),
        s = (function () {
          var t = Object(r["a"])(
            regeneratorRuntime.mark(function t(e) {
              return regeneratorRuntime.wrap(
                function (t) {
                  while (1)
                    switch ((t.prev = t.next)) {
                      case 0:
                        return (
                          (t.prev = 0),
                          (t.next = 3),
                          Object(i["a"])({
                            url: "/nwxhf/bill/getHistoricalBills",
                            method: "post",
                            data: e,
                          })
                        );
                      case 3:
                        return t.abrupt("return", t.sent);
                      case 6:
                        (t.prev = 6),
                          (t.t0 = t["catch"](0)),
                          console.error(t.t0);
                      case 9:
                      case "end":
                        return t.stop();
                    }
                },
                t,
                null,
                [[0, 6]]
              );
            })
          );
          return function (e) {
            return t.apply(this, arguments);
          };
        })(),
        u = (function () {
          var t = Object(r["a"])(
            regeneratorRuntime.mark(function t(e) {
              return regeneratorRuntime.wrap(
                function (t) {
                  while (1)
                    switch ((t.prev = t.next)) {
                      case 0:
                        return (
                          (t.prev = 0),
                          (t.next = 3),
                          Object(i["a"])({
                            url: "/nwxhf/bill/getHistoricalBillHead",
                            method: "post",
                            data: e,
                          })
                        );
                      case 3:
                        return t.abrupt("return", t.sent);
                      case 6:
                        (t.prev = 6),
                          (t.t0 = t["catch"](0)),
                          console.error(t.t0);
                      case 9:
                      case "end":
                        return t.stop();
                    }
                },
                t,
                null,
                [[0, 6]]
              );
            })
          );
          return function (e) {
            return t.apply(this, arguments);
          };
        })(),
        c = (function () {
          var t = Object(r["a"])(
            regeneratorRuntime.mark(function t(e) {
              return regeneratorRuntime.wrap(
                function (t) {
                  while (1)
                    switch ((t.prev = t.next)) {
                      case 0:
                        return (
                          (t.prev = 0),
                          (t.next = 3),
                          Object(i["a"])({
                            url: "/nwxhf/bill/getPendingBills",
                            method: "post",
                            data: e,
                          })
                        );
                      case 3:
                        return t.abrupt("return", t.sent);
                      case 6:
                        (t.prev = 6),
                          (t.t0 = t["catch"](0)),
                          console.error(t.t0);
                      case 9:
                      case "end":
                        return t.stop();
                    }
                },
                t,
                null,
                [[0, 6]]
              );
            })
          );
          return function (e) {
            return t.apply(this, arguments);
          };
        })(),
        l = (function () {
          var t = Object(r["a"])(
            regeneratorRuntime.mark(function t(e) {
              return regeneratorRuntime.wrap(
                function (t) {
                  while (1)
                    switch ((t.prev = t.next)) {
                      case 0:
                        return (
                          (t.prev = 0),
                          (t.next = 3),
                          Object(i["a"])({
                            url: "/nwxhf/bill/hasUSDCard",
                            method: "get",
                            data: e,
                            headers: {
                              noUnpackFlag: "1",
                            },
                          })
                        );
                      case 3:
                        return t.abrupt("return", t.sent);
                      case 6:
                        (t.prev = 6),
                          (t.t0 = t["catch"](0)),
                          console.error(t.t0);
                      case 9:
                      case "end":
                        return t.stop();
                    }
                },
                t,
                null,
                [[0, 6]]
              );
            })
          );
          return function (e) {
            return t.apply(this, arguments);
          };
        })();
    },
    "64a2": function (t, e, n) {},
  },
]);
