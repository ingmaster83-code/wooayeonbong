/* 홈 회사 검색: /assets/data/search.json = [이름, slug, 직원수, 시도, 시군구, 추정연봉(만원, 음수=상한 이상)] */
(function () {
  var q = document.getElementById('q'), box = document.getElementById('sr');
  if (!q || !box) return;
  var data = null, loading = false;
  function load(cb) {
    if (data) return cb();
    if (loading) return;
    loading = true;
    fetch('/assets/data/search.json').then(function (r) { return r.json(); }).then(function (j) { data = j; cb(); }).catch(function () { loading = false; });
  }
  function norm(s) { return s.replace(/\(주\)|주식회사|㈜|\s/g, '').toLowerCase(); }
  function render() {
    var t = norm(q.value);
    if (t.length < 1 || !data) { box.style.display = 'none'; return; }
    var starts = [], has = [];
    for (var i = 0; i < data.length && starts.length < 12; i++) {
      var n = norm(data[i][0]);
      var p = n.indexOf(t);
      if (p === 0) starts.push(data[i]); else if (p > 0 && has.length < 12) has.push(data[i]);
    }
    var res = starts.concat(has).slice(0, 12);
    if (!res.length) { box.innerHTML = '<a href="#" onclick="return false">검색 결과가 없습니다 (직원 30명 이상 법인만 수록)</a>'; box.style.display = 'block'; return; }
    box.innerHTML = res.map(function (r) {
      var sal = r[5] < 0 ? Math.abs(r[5]).toLocaleString('ko-KR') + '만원 이상' : '약 ' + r[5].toLocaleString('ko-KR') + '만원';
      return '<a href="/company/' + encodeURI(r[1]) + '/">' + r[0] + '<small>' + r[3] + ' ' + r[4] + ' · ' + r[2].toLocaleString('ko-KR') + '명 · ' + sal + '</small></a>';
    }).join('');
    box.style.display = 'block';
  }
  q.addEventListener('focus', function () { load(render); });
  q.addEventListener('input', function () { load(render); });
  document.addEventListener('click', function (e) { if (!box.contains(e.target) && e.target !== q) box.style.display = 'none'; });
})();
