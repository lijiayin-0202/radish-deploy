/* shop-trade 静态演示页面公共脚本：原生 fetch，不引入 Vue / 前端构建。 */
(function () {
  var pages = [
    ['index.html', '首页'],
    ['v01-goods.html', 'V-01 商品浏览'],
    ['v02-orders.html', 'V-02 我的订单'],
    ['v03-goods-admin.html', 'V-03 商品管理'],
    ['v04-ops-summary.html', 'V-04 运营核查'],
    ['v05-shipment-list.html', 'V-05 待发货'],
    ['v06-shipment-form.html', 'V-06 发货录入'],
    ['v07-refund-review.html', 'V-07 退款审核'],
    ['v08-late-payment.html', 'V-08 迟到支付']
  ];
  var accounts = ['buyer01', 'buyer02', 'buyer03', 'ops01', 'warehouse01', 'cs01', 'mock01'];

  function el(id) { return document.getElementById(id); }
  function val(id) { return el(id) ? (el(id).value || '').trim() : ''; }

  function init(defaultAccount) {
    var nav = el('nav');
    if (nav) {
      var current = location.pathname.split('/').pop() || 'index.html';
      nav.innerHTML = pages.map(function (p) {
        return '<a href="/static/' + p[0] + '" class="' + (p[0] === current ? 'current' : '') + '">' + p[1] + '</a>';
      }).join('');
    }
    var select = el('account');
    if (select) {
      select.innerHTML = accounts.map(function (a) {
        return '<option value="' + a + '"' + (a === defaultAccount ? ' selected' : '') + '>' + a + '</option>';
      }).join('');
    }
    show({ tip: '选择演示账号后点击按钮；响应统一为 code / message / data。身份只由 X-Demo-Account 解析。' });
  }

  function show(data) {
    var out = el('out');
    if (out) { out.textContent = JSON.stringify(data, null, 2); }
  }

  function call(path, method, body) {
    var opts = {
      method: method || 'GET',
      headers: { 'X-Demo-Account': val('account'), 'Content-Type': 'application/json' }
    };
    if (body) { opts.body = JSON.stringify(body); }
    return fetch(path, opts).then(function (res) {
      return res.json().catch(function () { return { http_status: res.status, parse_error: true }; });
    }).then(function (data) {
      show(data);
      return data;
    }).catch(function (err) {
      show({ error: String(err) });
      return null;
    });
  }

  function click(id, fn) {
    var node = el(id);
    if (node) { node.addEventListener('click', fn); }
  }

  function renderGoods(items) {
    var box = el('goodsTable');
    if (!box) { return; }
    if (!items || !items.length) { box.innerHTML = '<p class="hint">暂无商品</p>'; return; }
    box.innerHTML = '<table><thead><tr><th>ID</th><th>商品编号</th><th>名称</th><th>单价(分)</th><th>可售</th><th>占用</th><th>状态</th></tr></thead><tbody>' +
      items.map(function (g) {
        return '<tr><td>' + g.id + '</td><td>' + g.goods_no + '</td><td>' + (g.name || g.goods_name || '-') + '</td><td>' + g.unit_price +
          '</td><td>' + g.available_stock + '</td><td>' + g.occupied_stock + '</td><td>' + g.status + '</td></tr>';
      }).join('') + '</tbody></table>';
  }

  function loadGoods() {
    return call('/api/v1/goods').then(function (data) {
      if (data && data.data && data.data.items) { renderGoods(data.data.items); }
      return data;
    });
  }

  window.Shop = {
    init: init,
    show: show,
    call: call,
    click: click,
    val: val,
    loadGoods: loadGoods
  };
})();
