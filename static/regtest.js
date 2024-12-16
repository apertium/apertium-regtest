'use strict';

let state = {};
let corpora = [];

function esc_html(t) {
	return t.
		replace(/&/g, '&amp;').
		replace(/</g, '&lt;').
		replace(/>/g, '&gt;').
		replace(/"/g, '&quot;').
		replace(/'/g, '&apos;');
}

function dec_html(t) {
	return t.
		replace(/&lt;/g, '<').
		replace(/&gt;/g, '>').
		replace(/&quot;/g, '"').
		replace(/&apos;/g, "'").
		replace(/&amp;/g, '&');
}

// From http://stackoverflow.com/a/41417072/4374566
$.fn.isInViewport = function() {
	let elementTop = $(this).offset().top;
	let elementBottom = elementTop + $(this).outerHeight();

	let viewportTop = $(window).scrollTop();
	let viewportBottom = viewportTop + $(window).height();

	return elementBottom > viewportTop && elementTop < viewportBottom;
};

// From https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions
function esc_regex(t) {
	return t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// From https://gist.github.com/victornpb/7736865
function occurrences(string, subString, allowOverlapping) {
	if (subString.length <= 0) {
		return string.length + 1;
	}

	let n = 0;
	let pos = 0;
	let step = allowOverlapping ? 1 : subString.length;

	while (true) {
		pos = string.indexOf(subString, pos);
		if (pos >= 0) {
			++n;
			pos += step;
		}
		else {
			break;
		}
	}
	return n;
}

function detect_format(t) {
	let f = 'plain';
	if (/(^|\n)"<[^\n\t]+>"/.test(t) && /(^|\n);?\t"[^\n\t]+"/.test(t)) {
		f = 'cg';
	}
	else if (/(^|\n)&quot;&lt;[^\n\t]+&gt;&quot;/.test(t) && /(^|\n);?\t&quot;[^\n\t]+&quot;/.test(t)) {
		f = 'cg';
	}
	else if (/\S+\t[^+\s]+\+[^+\s]+/.test(t)) {
		f = 'fst';
	}
	else if (/\^.*\$/.test(t)) {
		f = 'ap';
	}
	return f;
}

function to_plain(t, f) {
	if (!f) {
		f = detect_format(t);
	}

	let plain = '';
	if (f === 'fst') {
		let last = '';
		let lines = t.split("\n");
		for (let i=0 ; i<lines.length ; ++i) {
			let ws = /^(\S+)\t/.exec(lines[i]);
			if (ws && ws[1]) {
				if (ws[1] !== last) {
					plain += ws[1]+' ';
				}
				last = ws[1];
			}
		}
	}
	else if (f === 'cg') {
		let lines = t.split("\n");
		for (let i=0 ; i<lines.length ; ++i) {
			let w = /^"<(.*)>"/.exec(lines[i]);
			if (w) {
				plain += w[1]+' ';
			}
		}
	}
	else {
		plain = t;
	}

	return $.trim(plain);
}

function hilite_output(t, f) {
	if (!f || f === 'auto' || f === "undefined") {
		f = detect_format(t);
	}

	if (f === 'fst') {
		t = t.replace(/\t([^+\n]+)(?=\+|\n|$)/g, '\t<span class="c-fst-b">$1</span>');
		t = t.replace(/\+([^\/+\n]+)(?=\+|\n|$)/g, '+<span class="c-fst-p">$1</span>');
		t = t.replace(/\+([^\/+\n]+\/[^+\n]+)(?=\+|\n|$)/g, '+<span class="c-fst-s">$1</span>');
		t = t.replace(/\+/g, '<span class="c-fst-pl">+</span>');
	}
	else if (f === 'cg') {
		let ls = t.split("\n");
		for (let i=0 ; i<ls.length ; ++i) {
			let ln = ls[i];
			if (/^(;?\t)(&quot;\S*[^&]+\S*&quot;)/.test(ln)) {
				ln = ln.replace(/ /g, '\t');
				let b = /^(;?\t)(&quot;\S*[^&]+\S*&quot;)(.*)$/.exec(ln);

				b[3] = b[3].replace(/(\t)(&lt;[^\s:]*:[^&:]+[^\s:]*&gt;)(?=\t|\n|$)/g, '$1<span class="c-cg-sc">$2</span>');
				b[3] = b[3].replace(/(\t)(&lt;\S*[^&]+\S*&gt;)(?=\t|\n|$)/g, '$1<span class="c-cg-s">$2</span>');
				b[3] = b[3].replace(/(\t)([@§£][^\s]+)(?=\t|\n|$)/g, '$1<span class="c-cg-m">$2</span>');
				b[3] = b[3].replace(/(\t)([-A-Z]+:\d+\S*)(?=\t|\n|$)/g, '$1<span class="c-cg-t">$2</span>');
				b[3] = b[3].replace(/(\t)((?![&@])[^\/\s]+\/[^\s]+)(?=\t|\n|$)/g, '$1<span class="c-cg-ps">$2</span>');
				b[3] = b[3].replace(/(\t)((?![&@])[^\/\s]+)(?=\t|\n|$)/g, '$1<span class="c-cg-p">$2</span>');

				ln = b[1]+'<span class="c-cg-b">'+b[2]+'</span>'+b[3];
				ln = ln.replace(/\t/g, ' ').replace(' ', '\t');
			}
			ls[i] = ln;
		}
		t = ls.join("\n");
	}
	else if (f === 'transfer') {
		t = t.replace(/(\[[^\n]+?\] \.\.\. [^\n]+)/g, '<span class="c-t-t">$1</span>');
	}
	else if (f == "ap") {
		//t = t.replace(/(\^|\/)(.+?)(?=\$|\/|&lt;)/g, '<span class="c-ap-d">$1</span><span class="c-ap-l">$2</span>');
		t = t.replace(/(\^|\/)(.+?)(?=\$|\/|&lt;)/g, function(m, d, lm) {
			let ret = '<span class="c-ap-d">'+d+'</span><span class="c-ap-';
			ret += (lm[0] == '*' ? 'u' : 'l');
			ret += '">'+lm+'</span>';
			return ret;
		});
		t = t.replace(/((?:&lt;\w+&gt;)+)/g, '<span class="c-ap-t">$1</span>');
		t = t.replace(/(\$|\{|\})/g, '<span class="c-ap-d">$1</span>');
	}

	return t;
}

function tokenize_stream(s) {
	let ret = [];
	let cur = "";
	let esc = false;
	let word = false;
	let blank = false;
	let wblank = false;
	for (let i = 0; i < s.length; i++) {
		if (esc) {
			esc = false;
		} else if (s[i] == '\\') {
			esc = true;
		} else if (wblank) {
			if (s[i] == ']' && i+1 < s.length && s[i+1] == ']') {
				wblank = false;
			}
		} else if (blank) {
			if (s[i] == ']') {
				blank = false;
			}
		} else if (!word && s[i] == '[') {
			blank = true;
			if (i+1 < s.length && s[i+1] == '[') {
				wblank = true;
			}
		} else if (!word && s[i] == '^' || s[i] == '}') {
			word = true;
			if (cur.length) {
				ret.push(cur);
				cur = "";
			}
		} else if (word && s[i] == '$' || s[i] == '{') {
			cur += s[i];
			ret.push(cur);
			cur = "";
			word = false;
			continue;
		}
		cur += s[i];
	}
	if (cur.length) {
		ret.push(cur);
	}
	return ret;
}

function tokenize_lu(s) {
	let ret = [];
	let cur = '';
	let esc = false;
	for (let i = 0; i < s.length; i++) {
		if (esc) {
		} else if (s[i] == '\\') {
			esc = true;
		} else if (s[i] == '/') {
			ret.push(cur);
			cur = '';
		}
		cur += s[i];
	}
	ret.push(cur);
	return ret;
}

function diff_lus(del_obj, add_obj) {
	if (add_obj.removed) {
		return diff_lus(add_obj, del_obj);
	}
	let del = del_obj.value;
	let add = add_obj.value;
	let out = '';
	for (let i = 0; i < del.length; i++) {
		if (del[i][0] == '^' && add[i][0] == '^') {
			out += '<span class="c-ap-lu">';
			let arr_d = tokenize_lu(del[i]);
			let arr_a = tokenize_lu(add[i]);
			let diff = Diff.diffArrays(arr_d, arr_a);
			for (let d = 0; d < diff.length; d++) {
				if (diff[d].added) {
					out += '<ins>';
					out += esc_html(diff[d].value.join(''));
					out += '</ins>';
				} else if (diff[d].removed) {
					out += '<del>';
					out += esc_html(diff[d].value.join(''));
					out += '</del>';
				} else {
					for (let j = 0; j < diff[d].value.length; j++) {
						out += hilite_output(diff[d].value[j], 'ap');
					}
				}
			}
			out += '</span>';
		} else {
			out += '<del>'+esc_html(del[i])+'</del>';
			out += '<ins>'+esc_html(add[i])+'</ins>';
		}
	}
	return out;
}

function diff_stream(exp, txt) {
	let arr_e = tokenize_stream(exp);
	let arr_t = tokenize_stream(txt);
	let diff = Diff.diffArrays(arr_e, arr_t);
	let output = '';
	for (let n = 0; n < diff.length; n++) {
		if (diff[n].added || diff[n].removed) {
			if (n + 1 < diff.length && (diff[n+1].added || diff[n+1].removed)
				&& diff[n+1].value.length == diff[n].value.length) {
				output += diff_lus(diff[n], diff[n+1]);
				n++;
			} else {
				output += (diff[n].added ? '<ins>' : '<del>');
				for (let n2 = 0; n2 < diff[n].value.length; n2++) {
					if (diff[n].value[n2][0] == '^') {
						output += '<span class="c-ap-lu">';
					}
					output += esc_html(diff[n].value[n2]);
					if (diff[n].value[n2][0] == '^') {
						output += '</span>';
					}
				}
				output += (diff[n].added ? '</ins>' : '</del>');
			}
		} else {
			let collapse = -1;
			if (diff[n].value.length > 15) {
				collapse = diff[n].value.length - 3;
			}
			for (let n2 = 0; n2 < diff[n].value.length; n2++) {
				if (diff[n].value[n2][0] == '^') {
					output += '<span class="c-ap-lu">';
				}
				output += hilite_output(esc_html(diff[n].value[n2]), 'ap');
				if (diff[n].value[n2][0] == '^') {
					output += '</span>';
				}
				if (collapse != -1 && n2 == 2) {
					output += '<div class="rt-expansion"><span class="rt-expanded">';
				}
				else if (n2 == collapse) {
					output += '</span><button tabindex="-1" type="button" class="btn btn-outline-secondary btn-sm btnExpand">…</button><button tabindex="-1" type="button" class="btn btn-outline-secondary btn-sm btnCollapse">…</button></div>';
				}
			}
		}
	}
	return output;
}

function ajax_fail(e) {
	console.log(e);
	if (e.hasOwnProperty('responseJSON')) {
		toast('<span class="text-danger">Error '+e.status+'</span>', e.responseJSON.error);
		return;
	}
	toast('<span class="text-danger">Error '+e.status+'</span>', e.responseText);
}

function post(data) {
	return $.post('callback', data).fail(ajax_fail);
}

function init() {
	let tid = toast('Initializing', 'Loading meta-data...');
	post({a: 'init'}).done(function(rv) { $(tid).toast('hide'); return cb_init(rv); });
}

function load(p) {
	let tid = toast('Loading', 'Loading page '+(p+1)+'...');
	post({a: 'load', p: p}).done(function(rv) { $(tid).toast('hide'); return cb_load(rv); });
}

function toast(title, body, delay) {
	let h = new Date().getHours();
	let m = new Date().getMinutes();
	let stamp = (h < 10 ? ('0'+h) : h)+':'+(m < 10 ? ('0'+m) : m);
	let id = 'toast-'+Date.now()+'-'+(''+Math.random()).replace(/[^\d]+/g, '');
	let html = '<div class="toast" id="'+id+'"><div class="toast-header"><strong class="mr-auto">'+title+'</strong> <small>'+stamp+'</small><button tabindex="-1" type="button" class="ml-2 mb-1 btn-close" data-bs-dismiss="toast" aria-label="Close"></button></div><div class="toast-body">'+body+'</div></div>';
	$('#toasts').append(html);
	id = '#'+id;
	$(id).on('hidden.bs.toast', function() { console.log('Toasted '+$(this).attr('id')); $(this).remove(); });
	if (delay) {
		$(id).toast({animation: false, delay: delay})
	}
	else {
		$(id).toast({animation: false, autohide: false})
	}
	$(id).toast('show');

	return id;
}

function btn_filter() {
	let which = $(this).attr('data-which');
	console.log('Filtering for corpus '+which);
	if (which === '*') {
		$('.corp').show();
	}
	else {
		$('.corp').hide();
		$('.corp-'+which).show();
	}
	$('.btnFilter').removeClass('active');
	$(this).addClass('active');
}

function btn_filter_gold() {
	let which = $(this).attr('data-which');
	console.log('Filtering by criterion '+which);
	if (which === '*') {
		$('.rt-filter-all').removeClass('rt-filter-gold-hidden');
	} else {
		$('.rt-filter-all').addClass('rt-filter-gold-hidden');
		$('.rt-filter-'+which).removeClass('rt-filter-gold-hidden');
	}
	apply_filters();
	$('.btnFilterGold').removeClass('active');
	$(this).addClass('active');
}

function apply_filters() {
	$('.rt-filter-all').hide();
	$('.rt-filter-all').not('.rt-filter-unchanged-hidden').not('.rt-filter-gold-hidden').show();
	update_counts();
	event_scroll();
}

function btn_run() {
	let c = $(this).attr('data-which');
	let tid = toast('Running Test', 'Launching regression test for: '+c+'<br>Check your terminal for progress.');
	post({a: 'run', c: c}).done(function(rv) { $(tid).toast('hide'); return cb_run(rv); });
}

function accept_multiple(c, hs, s) {
	let tid = toast('Accepting Multiple', 'Corpus '+c+' sentence '+hs.join(" "));
	post({a: 'accept', c: c, s: s, hs: hs.join(';')}).done(function(rv) { $(tid).toast('hide'); cb_accept(rv); });
}

function _diff_toggle(where, show, hide) {
	let div = $(where).closest('tr').find('.tab-pane:visible');
	div.find('ins,del');
	div.find(show).show();
	if (hide) {
		div.find(hide).hide();
	}
}

function select_diff() {
	let div = $(this).closest('tr').find('.tab-pane:visible');
	div.find('ins,del').hide();
	div.find($(this).val()).show();
}

function btn_diff_both() {
	return _diff_toggle(this, 'ins,del');
}

function btn_diff_ins() {
	return _diff_toggle(this, 'ins', 'del');
}

function btn_diff_del() {
	return _diff_toggle(this, 'del', 'ins');
}

function btn_collapse() {
	let div = $(this).closest('div');
	div.children('span').hide();
	$(this).hide();
	div.find('.btnExpand').show();
}

function btn_expand() {
	let div = $(this).closest('div');
	div.children('span').show();
	$(this).hide();
	div.find('.btnCollapse').show();
}

function btn_gold_replace() {
	let tr = $(this).closest('tr');
	let c = tr.attr('data-corp');
	let h = tr.attr('data-hash');
	let s = tr.find('.nav-link.active').text();
	let gs = [tr.find('.rt-output.active').attr('data-output')];
	let tid = toast('Replacing Gold', 'Corpus '+c+' sentence '+h+' step '+s);
	post({a: 'gold', c: c, h: h, s: s, gs: JSON.stringify(gs)}).done(function(rv) { $(tid).toast('hide'); cb_accept(rv); });
}

function btn_gold_add() {
	let tr = $(this).closest('tr');
	let c = tr.attr('data-corp');
	let h = tr.attr('data-hash');
	let s = tr.find('.nav-link.active').text();
	let gs = [];
	let gold = state[c].cmds[state[c].cmds.length-1].gold;
	if (gold.hasOwnProperty(h)) {
		gs = gold[h];
	}
	gs.push(tr.find('.rt-output.active').attr('data-output'));
	let tid = toast('Adding Gold', 'Corpus '+c+' sentence '+h+' step '+s);
	post({a: 'gold', c: c, h: h, s: s, gs: JSON.stringify(gs)}).done(function(rv) { $(tid).toast('hide'); cb_accept(rv); });
}

function btn_gold_manual() {
	let tr = $(this).closest('tr');
	let val = tr.find('.rt-output.active').attr('data-output');
	tr.find('.rt-gold-input').show().find('input').val(val);
}

function btn_gold_manual_accept() {
	let tr = $(this).closest('tr');
	let c = tr.attr('data-corp');
	let h = tr.attr('data-hash');
	let s = tr.find('.nav-link.active').text();
	let gs = [];
	let gold = state[c].cmds[state[c].cmds.length-1].gold;
	if (gold.hasOwnProperty(h)) {
		gs = gold[h];
	}
	gs.push(tr.find('.rt-gold-input-box').val());
	let tid = toast('Adding Gold', 'Corpus '+c+' sentence '+h+' step '+s);
	post({a: 'gold', c: c, h: h, s: s, gs: JSON.stringify(gs)}).done(function(rv) { $(tid).toast('hide'); cb_accept(rv); });
	let tab = tr.find('.rt-output.active');
	tab.find('.rt-gold').remove();
	tab.append(make_gold_list(gs));
}

function btn_gold_manual_cancel() {
	let tr = $(this).closest('tr');
	tr.find('.rt-gold-input').hide();
}

function btn_accept() {
	let tr = $(this).closest('tr');
	let c = tr.attr('data-corp');
	let h = tr.attr('data-hash');
	let tid = toast('Accepting Single', 'Corpus '+c+' sentence '+h);
	post({a: 'accept', c: c, hs: [h].join(';')}).done(function(rv) { $(tid).toast('hide'); cb_accept(rv); });
}

function btn_accept_until() {
	let tr = $(this).closest('tr');
	let c = tr.attr('data-corp');
	let s = tr.find('a.nav-link.active').text();
	let h = tr.attr('data-hash');
	let tid = toast('Accepting Partial', 'Corpus '+c+', step '+s+', sentence '+h);
	post({a: 'accept', c: c, s: s, hs: [h].join(';')}).done(function(rv) { $(tid).toast('hide'); cb_accept(rv); });
}

function btn_accept_all() {
	$('.rt-changes').find('span.corp').filter(':visible').each(function() {
		let hs = [];
		$(this).find('tr').each(function() {
			hs.push($(this).attr('data-hash'));
		});
		accept_multiple($(this).attr('data-corp'), hs);
	});
}

function btn_accept_all_until() {
	let step = $(this).attr('data-step');
	$('.rt-changes').find('span.corp').filter(':visible').each(function() {
		let hs = [];
		$(this).find('tr').each(function() {
			hs.push($(this).attr('data-hash'));
		});
		accept_multiple($(this).attr('data-corp'), hs, step);
	});
}

function btn_accept_unchanged() {
	$('.rt-changes').find('span.corp').filter(':visible').each(function() {
		let hs = [];
		$(this).find('tr').not('.rt-changed-result').each(function() {
			hs.push($(this).attr('data-hash'));
		});
		accept_multiple($(this).attr('data-corp'), hs);
	});
}

function btn_accept_nd() {
	let c = $(this).attr('data-corp');
	let tid = toast('Accepting Added/Deleted', 'Corpus '+c);
	post({a: 'accept-nd', c: c}).done(function(rv) { $(tid).toast('hide'); cb_accept_nd(rv); });
}

function btn_toggle_unchanged() {
	let hidden = $('.rt-filter-unchanged-hidden');
	if (hidden.length) {
		hidden.removeClass('rt-filter-unchanged-hidden');
	} else {
		$('.rt-changes').find('tr').not('.rt-changed-result').addClass('rt-filter-unchanged-hidden');
	}
	apply_filters();
}

function btn_checked_gold_replace() {
	$('.rt-change-tick:checked').filter(':visible').each(btn_gold_replace);
}

function btn_checked_gold_add() {
	$('.rt-change-tick:checked').filter(':visible').each(btn_gold_add);
}

function btn_checked_accept() {
	$('.rt-changes').find('span.corp').filter(':visible').each(function() {
		let hs = [];
		$(this).find('.rt-change-tick:checked').filter(':visible').each(function() {
			hs.push($(this).closest('tr').attr('data-hash'));
		});
		accept_multiple($(this).attr('data-corp'), hs);
	});
}

function btn_checked_accept_until() {
	let step = $(this).attr('data-step');
	$('.rt-changes').find('span.corp').filter(':visible').each(function() {
		let hs = [];
		$(this).find('.rt-change-tick:checked').filter(':visible').each(function() {
			hs.push($(this).closest('tr').attr('data-hash'));
		});
		accept_multiple($(this).attr('data-corp'), hs, step);
	});
}

function btn_checked_invert() {
	$('.rt-change-tick').filter(':visible').each(function() {
		$(this).prop('checked', !$(this).prop('checked'));
	});
}

function enable_disable_btn(setting, row, clss, btntype) {
	if (setting) {
		clss.forEach(function (cls) {
			row.find(cls).removeClass('disabled').prop('disabled', false).removeClass('btn-outline-secondary').addClass(btntype);
		});
	} else {
		clss.forEach(function (cls) {
			row.find(cls).addClass('disabled').prop('disabled', true).addClass('btn-outline-secondary').removeClass(btntype);
		});
	}
}

function btn_show_tab() {
	// Set text and en-/disable partial accept button
	let row = $(this).closest('tr');
	row.find('.btnAcceptUntil').text('Accept: '+$(this).text());
	enable_disable_btn($(this).hasClass('rt-changed'), row,
					   ['.btnAcceptUntil'], 'btn-outline-success');
	enable_disable_btn($(this).hasClass('rt-changed'), row,
					   ['.selectDiffMode'], 'btn-outline-primary');
	enable_disable_btn($(this).hasClass('rt-tab-has-gold'), row,
					   ['.btnGoldReplace'], 'btn-outline-warning');

	// Highlight syntax, if in view and not already done
	if ($(this).attr('data-hilite') || !$(this).isInViewport()) {
		return;
	}
	let div = $($(this).attr('href'));

	let type = div.attr('data-type');
	let text = div.attr('data-output');
	let expect = div.attr('data-expect');
	if (!type || type === 'auto' || type === 'undefined') {
		type = detect_format(text);
	}

	if (expect) {
		let output = '';
		if (type === 'ap') {
			output = diff_stream(expect, text);
		} else {
			let diff = null;
			if (occurrences(expect, '\n') >= 100) {
				diff = Diff.diffLines(expect, text);
			}
			else {
				diff = Diff.diffWordsWithSpace(expect, text);
			}
			for (let d=0 ; d<diff.length ; ++d) {
				if (diff[d].added) {
					output += '<ins>'+esc_html(diff[d].value)+'</ins>';
				}
				else if (diff[d].removed) {
					output += '<del>'+esc_html(diff[d].value)+'</del>';
				}
				else {
					let val = esc_html(diff[d].value);
					if (/\n([^\n]+\n){6}/.test(val)) {
						let ls = val.split("\n");
						val = hilite_output(ls[0]+"\n"+ls[1]+"\n"+ls[2]+"\n", type);
						val += '<div class="rt-expansion"><span class="rt-expanded">'+hilite_output(ls.slice(3, -3).join("\n"), type)+'</span><button tabindex="-1" type="button" class="btn btn-outline-secondary btn-sm btnExpand">…</button><button tabindex="-1" type="button" class="btn btn-outline-secondary btn-sm btnCollapse">…</button></div>';
						val += hilite_output(ls[ls.length-3]+"\n"+ls[ls.length-2]+"\n"+ls[ls.length-1], type);
					}
					else {
						val = hilite_output(val, type);
					}
				output += val;
				}
			}
		}
		$(div).find('pre').html(output);
		div.removeAttr('data-expect');
		div.find('.rt-expanded').hide();
		div.find('.btnExpand').off().click(btn_expand);
		div.find('.btnCollapse').off().click(btn_collapse).hide();
	}
	else {
		$(div).find('pre').html(hilite_output(esc_html(text), type));
	}

	$(this).attr('data-hilite', true);
}

function click_and_show(e) {
	e.click();
	bootstrap.Tab.getOrCreateInstance(e.get(0)).show();
}

function btn_select_tab() {
	let which = $(this).attr('data-which');
	if (which === '*FIRST') {
		$('.rt-changes').find('tr').filter(':visible').each(function() {
			click_and_show($(this).find('a.rt-changed').first());
		});
	}
	else if (which === '*LAST') {
		$('.rt-changes').find('tr').filter(':visible').each(function() {
			click_and_show($(this).find('a.rt-changed').last());
		});
	}
	else {
		$('.rt-tab-'+which).filter(':visible').each(function() {
			click_and_show($(this));
		});
	}

	if (which === '*FIRST' || which === '*LAST') {
		$('.btnAcceptAllUntil,.btnCheckedAcceptUntil').addClass('disabled').prop('disabled', true);
	}
	else {
		$('.btnAcceptAllUntil,.btnCheckedAcceptUntil').show().removeClass('disabled').prop('disabled', false).attr('data-step', which);
		$('.btnAcceptAllUntil').text('Accept All: '+which);
		$('.btnCheckedAcceptUntil').text('Accept Checked: '+which);
	}

	$('.btnSelectTab').removeClass('active');
	$(this).addClass('active');
}

function btn_page() {
	let p = $(this).attr('data-which');
	if (p === 'prev') {
		load(Math.max(0, state._page-1));
	}
	else if (p === 'next') {
		load(Math.min(state._pages-1, state._page+1));
	}
	else {
		load(parseInt(p));
	}
	return false;
}

function update_counts() {
	let changed = 0;

	$('.rt-count-corp').each(function() {
		let s = $(this).closest('span.corp');
		let t = state[s.attr('data-corp')].count;
		let ch = s.find('tr:visible').length;
		$(this).text('('+ch+' of '+t+' ; '+Math.round(ch*1000.0/t)/10.0+'%)');

		changed += ch;
	});

	$('.rt-count-total').text('('+changed+' of '+state._count+' ; '+Math.round(changed*1000.0/state._count)/10.0+'%)');
}

function cb_init(rv) {
	let txt = 'Regtest: '+rv.folder;
	if (rv.step) {
		txt += ' -s '+rv.step;
	}
	$('title,#title').text(txt);

	let html_filter = '';
	let html_run = '';
	corpora = rv.corpora;
	corpora.sort();
	for (let i=0 ; i<corpora.length ; ++i) {
		html_filter += ' <button tabindex="-1" type="button" class="btn btn-sm btn-outline-primary my-1 btnFilter" data-which="'+esc_html(corpora[i])+'">'+esc_html(corpora[i])+'</button>';
		html_run += ' <button tabindex="-1" type="button" class="btn btn-sm btn-outline-info my-1 btnRun" data-which="'+esc_html(corpora[i])+'">'+esc_html(corpora[i])+'</button>';
	}
	$('#rt-corpora-filter').replaceWith(html_filter);
	$('#rt-corpora-run').replaceWith(html_run);

	$('.btnFilter').off().click(btn_filter);
	$('.btnRun').off().click(btn_run);
	$('.btnFilterGold').off().click(btn_filter_gold);
}

function btn_gold_edit(goldText) {
    let tr = $(this).closest('tr');
    let c = tr.attr('data-corp');
    let h = tr.attr('data-hash');
    let s = tr.find('.nav-link.active').text();
    let gs = [];
    let gold = state[c].cmds[state[c].cmds.length - 1].gold;

    if (gold.hasOwnProperty(h)) {
        gs = gold[h];
    }

    let currentGold = goldText; 
    let newGold = prompt('Edit Gold:', currentGold);

    if (newGold !== null && newGold.trim() !== '') {
        let index = gs.indexOf(currentGold);
        if (index !== -1) {
            gs[index] = newGold;
        }
        let tid = toast('Editing Gold', 'Corpus ' + c + ' sentence ' + h + ' step ' + s);
        post({ a: 'gold', c: c, h: h, s: s, gs: JSON.stringify(gs) }).done(function (rv) {
            $(tid).toast('hide');
            cb_accept(rv);
        });
    }
}


function btn_gold_delete() {
    let li = $(this).closest('li'); 
    let tr = li.closest('tr'); 
    let c = tr.attr('data-corp');
    let h = tr.attr('data-hash');
    let s = tr.find('.nav-link.active').text();
    let gs = [];
    let gold = state[c].cmds[state[c].cmds.length-1].gold;

    if (gold.hasOwnProperty(h)) {
        gs = gold[h];
    }

    let currentGold = li.text().trim(); 
    let index = gs.indexOf(currentGold);
    if (index !== -1) {
        gs.splice(index, 1); 
    }

    let tid = toast('Deleting Gold', 'Corpus ' + c + ' sentence ' + h + ' step ' + s);
    post({ a: 'gold', c: c, h: h, s: s, gs: JSON.stringify(gs) }).done(function (rv) {
        $(tid).toast('hide');
        cb_accept(rv);
    });

    li.remove();
}


function make_gold_list(golds) {
    let ul = '<ul class="list-group rt-gold">';
    ul += golds.map(g => {
        return `
            <li class="list-group-item d-flex justify-content-between align-items-center">
                <span class="gold-text">${esc_html(g)}</span>
                <div class="btn-container">
                    <button type="button" class="btn btn-sm btn-outline-info my-2 btnEditGold">Edit</button>
                    <button type="button" class="btn btn-sm btn-outline-danger my-2 btnDeleteGold">Delete</button>
                </div>
            </li>`;
    }).join('');
    ul += '</ul>';
    return ul;
}


function cb_load(rv) {
	$('.rt-added,.rt-deleted,.rt-add-del-warn,.rt-deleted').hide();
	$('#rt-added,#rt-deleted').find('tbody').remove();
	$('#rt-changes').text('');
	$('#rt-corpora-tabs').text('');

	let tabs = {};
	let tabs_html = '';
	let nd_corps = {};

	state = rv.state;

	$(document).on('click', '.rt-gold .btnEditGold', function () {
		let li = $(this).closest('li');  
		let goldText = li.find('.gold-text').text();  
		btn_gold_edit.call(this, goldText);  
	});
	
	$(document).on('click', '.rt-gold .btnDeleteGold', function () {
		btn_gold_delete.call(this); 
	});	

	let pages = '';
	if (state._pages > 1) {
		pages += '<ul class="pagination"><li class="page-item"><a class="page-link rt-page rt-page-prev" href="#" data-which="prev">&laquo;</a></li>';
		for (let p=0 ; p<state._pages ; ++p) {
			let cur = '';
			if (p === state._page) {
				cur = ' active';
			}
			pages += '<li class="page-item'+cur+'"><a class="page-link rt-page rt-page-'+p+'" href="#" data-which="'+p+'">'+(p+1)+'</a></li>';
		}
		pages += '<li class="page-item"><a class="page-link rt-page rt-page-next" href="#" data-which="next">&raquo;</a></li></ul>';
	}
	$('.rt-pages').html(pages);
	$('.rt-page').click(btn_page);

	let add_html = '';
	let del_html = '';

	corpora.forEach(function(c) {
		state[c].changed_end = '';
		state[c].changed_any = '';
		state[c].unchanged = '';

		let cmds = state[c].cmds;
		let ins = state[c].inputs;
		let outs = cmds[0].expect;
		let add = state[c].add;
		let del = state[c].del;

		if (add.length) {
			add_html += '<tr class="corp-'+c+'"><td>'+c+'</td><td>'+add.length+'</td><td>'+add.join(' ')+'</td></tr>';
			nd_corps[c] = true;
		}

		if (del.length) {
			del_html += '<tr class="corp-'+c+'"><td>'+c+'</td><td>'+del.length+'</td><td>'+del.join(' ')+'</td></tr>';
			nd_corps[c] = true;
		}

		let ks = [];
		for (let k in ins) {
			if (outs.hasOwnProperty(k)) {
				ks.push(k);
			}
		}
		ks.sort(function(a, b) {
			return ins[a][0] - ins[b][0];
		});

		let changes = false;

		for (let ki=0 ; ki<ks.length ; ++ki) {
			let k = ks[ki];

			let changed = false;
			let changed_result = '';
			let bucket = 'unchanged';
			let nav = '<ul class="nav nav-tabs" role="tablist">';
			let body = '<div class="tab-content">';

			let id = c+'-'+k+'-input';
			body += '<pre class="rt-input">'+esc_html(ins[k][1])+'</pre>';

			let filter_no_gold = true;
			let filter_unmatched_gold = false;

			for (let i=0 ; i<cmds.length ; ++i) {
				let cmd = cmds[i];
				if (!cmd.output.hasOwnProperty(k)) {
					continue;
				}
				if (!cmd.expect.hasOwnProperty(k)) {
					continue;
				}

				let output = esc_html(cmd.output[k][1]);
				let style = '';
				let expect = '';
				if (cmd.output[k][1] !== cmd.expect[k][1]) {
					if (!changed) {
						style += ' show active';
						bucket = 'changed_any';
					}
					style += ' rt-changed';
					changed = true;
					if (cmd.gold.hasOwnProperty(k) && cmd.gold[k].indexOf(cmd.output[k][1]) != -1) {
						style += ' rt-gold';
					} else if (cmd.relevant) {
						changed_result = ' rt-changed-result';
						bucket = 'changed_end';
					}

					expect = ' data-expect="'+esc_html(cmd.expect[k][1])+'"';
				}
				if (i == cmds.length-1) {
					style += ' rt-last-tab';
					if (!changed) {
						style += ' show active';
					}
				}
				if (cmd.gold.hasOwnProperty(k)) {
					style += ' rt-tab-has-gold';
				}

				if (cmd.gold.hasOwnProperty(k) && cmd.gold[k].length) {
					filter_no_gold = false;
					if (cmd.gold[k].indexOf(cmd.output[k][1]) == -1) {
						filter_unmatched_gold = true;
					}
				}

				if (!tabs.hasOwnProperty(cmd.opt)) {
					tabs[cmd.opt] = true;
					tabs_html += '<button tabindex="-1" type="button" class="btn btn-sm btn-outline-primary my-1 btnSelectTab" data-which="'+cmd.opt+'" title="'+esc_html(cmd.cmd)+'">'+cmd.opt+'</button>\n';
				}

				let id = c+'-'+k+'-'+cmd.opt;
				nav += '<li class="nav-item"><a tabindex="-1" class="nav-link rt-tab-'+cmd.opt+style+'" id="'+id+'-tab" data-bs-toggle="tab" href="#'+id+'" role="tab">'+cmd.opt+'</a></li>';
				body += '<div class="tab-pane'+style+' rt-output p-1" id="'+id+'" role="tabpanel" data-type="'+cmd.type+'"'+expect+' data-output="'+output+'"><pre>'+output+'</pre>';

				if (cmd.gold.hasOwnProperty(k)) {
					body += make_gold_list(cmd.gold[k]);
				}
				body += '</div>';

				if (cmd.trace.hasOwnProperty(k)) {
					let id = c+'-'+k+'-'+cmd.opt+'-trace';
					nav += '<li class="nav-item"><a tabindex="-1" class="nav-link" id="'+id+'-tab" data-bs-toggle="tab" href="#'+id+'" role="tab">-trace</a></li>';
					body += '<pre class="tab-pane rt-output p-1" id="'+id+'" role="tabpanel" data-type="'+cmd.type+'">'+esc_html(cmd.trace[k][1])+'</pre>';
				}
			}

			body += '</div>';
			nav += '</ul>';
			if (changed) {
				changes = true;
			}
			else {
				changed_result = ' rt-unchanged';
			}

			let btn_types = [
				// class, label, trailing space
				["success btnAcceptUntil", "…", ' <span class="rtGold">&nbsp; ',
				 "accept changes of current and prior steps"],
				["warning btnGoldReplace", "Replace as Gold", " ",
				 "remove gold value(s) and replace with current output"],
				["warning btnGoldAdd", "Add as Gold", " ",
				 "add current output to list of gold values"],
				["warning btnGoldManual", "Add Manual Gold ↓", "</span> &nbsp; ",
				 "manually enter gold value"],
				["success btnAccept", "Accept Result", " ",
				 "accept the entire output for this entry"]
			];

			let filter_class = 'rt-filter-all';
			if (filter_no_gold) {
				filter_class += ' rt-filter-no-gold';
			}
			if (filter_unmatched_gold) {
				filter_class += ' rt-filter-unmatched-gold';
			}
			state[c][bucket] += '<tr data-corp="'+c+'" data-hash="'+k+'" class="'+changed_result+' '+filter_class+' hash-'+k+'"><td>'+nav+body+'<div class="text-right my-1">';
			state[c][bucket] += '<select class="form-select form-select-sm selectDiffMode" title="Hide insertions or deletions in diff"><option selected value="ins,del">Diff</option><option value="ins">Inserted</option><option value="del">Deleted</option></select>&nbsp;';
			state[c][bucket] += btn_types.map(function(b) {
				return '<button tabindex="-1" type="button" class="btn btn-sm btn-outline-'+b[0]+'" title="'+b[3]+'">'+b[1]+'</button>'+b[2];
			}).join('');
			state[c][bucket] += '<input type="checkbox" class="mx-2 align-middle rt-change-tick"></div><div class="text-right my-1 rt-gold-input"><input type="text" class="rt-gold-input-box"></input> <button tabindex="-1" type="button" class="btn btn-sm btn-outline-warning btnGoldManualAccept">Add as Gold</button> <button tabindex="-1" type="button" class="btn btn-sm btn-outline-primary btnGoldManualCancel">Cancel</button></div></td></tr>'+"\n";
		}
	});

	if (add_html) {
		add_html = '<tbody class="corp"><tr><th>Corpus</th><th>Added Lines</th><th>Hashes</th></tr>' + add_html + '</tbody>';
		$('#rt-added').append(add_html);
		$('.rt-added,.rt-add-del-warn').show();
	}
	if (del_html) {
		del_html = '<tbody class="corp"><tr><th>Corpus</th><th>Deleted Lines</th><th>Hashes</th></tr>' + del_html + '</tbody>';
		$('#rt-deleted').append(del_html);
		$('.rt-deleted,.rt-add-del-warn').show();
	}

	$('#rt-corpora-tabs').html(tabs_html);

	let nd_btns = '';
	Object.keys(nd_corps).forEach(function(c) {
		nd_btns += '<button class="btn btn-outline-success btnAcceptND" data-corp="'+c+'">Accept added/deleted: '+c+'</button> ';
	});
	if (nd_btns) {
		$('#rt-nd-btns').html(nd_btns);
		$('.btnAcceptND').click(btn_accept_nd);
	}

	const BUCKETS = {
		changed_end: 'Changed Result',
		changed_any: 'Changed',
		unchanged: 'Unchanged',
		};
	let html = '';
	['changed_end', 'changed_any', 'unchanged'].forEach(function(b) {
		corpora.forEach(function(c) {
			if (state[c][b]) {
				html += '<span class="corp corp-'+c+'" data-corp="'+c+'"><h3>'+BUCKETS[b]+': '+c+' <span class="rt-count rt-count-corp"></span></h3><table class="table table-bordered table-sm my-1">';
				html += state[c][b];
				html += '</table></span>';
			}
		});
	});

	$('#rt-changes').html(html);
	$('.rt-changes').show();

	$('.btnSelectTab').off().click(btn_select_tab);
	$('.selectDiffMode').off().change(select_diff);
	$('.btnGoldReplace').off().click(btn_gold_replace);
	$('.btnGoldAdd').off().click(btn_gold_add);
	$('.btnGoldManual').off().click(btn_gold_manual);
	$('.btnGoldManualAccept').off().click(btn_gold_manual_accept);
	$('.btnGoldManualCancel').off().click(btn_gold_manual_cancel);
	$('.btnAcceptUntil').off().click(btn_accept_until);
	$('.btnAccept').off().click(btn_accept);
	$('.nav-link').off().click(btn_show_tab);

	$('.rt-gold-input').hide();

	if ($('.btnFilter.active').attr('data-which') !== '*') {
		$('.btnFilter.active').click();
	}

	let nchange = $('.rt-changed-result:visible').length;
	let tab = null;
	if (nchange) {
		btn_toggle_unchanged();
	}
	if (state['_step'] && state['_step'] !== '*') {
		let tabs = $('#rt-corpora-tabs').find('.btnSelectTab');
		let pt = null;
		for (let i=0 ; i<tabs.length ; ++i) {
			if (tabs.eq(i).text() === state['_step']) {
				tab = tabs.eq(i);
				break;
			}
			if (!pt && tabs.eq(i).text().indexOf(state['_step']) === 0) {
				pt = tabs.eq(i);
			}
		}
		if (!tab) {
			tab = pt;
		}
	}
	if (!tab && nchange) {
		tab = $('#rt-corpora-tabs').find('.btnSelectTab').last();
	}
	if (tab) {
		tab.click();
	}

	update_counts();
	setTimeout(event_scroll, 100);
}

function cb_run(rv) {
	if (rv.good) {
		toast('Run Output', '<b>Success</b><br><b>Output:</b><br><code>'+esc_html(rv.output).replace(/\n/g, '<br>')+'</code>', 7000);
		load(0);
	}
	else {
		toast('Run Output', '<b>Error</b><br><b>Output:</b><br><code>'+esc_html(rv.output).replace(/\n/g, '<br>')+'</code>');
	}
}

function cb_accept(rv) {
	for (let i=0 ; i<rv.hs.length ; ++i) {
		$('.hash-'+rv.hs[i]).fadeOut(500, function() { $(this).remove(); });
	}
	$('.rt-add-del-warn').hide();
	setTimeout(function() {
		update_counts();
		event_scroll();
		}, 600);
}

function cb_accept_nd(rv) {
	let s = ['#rt-added', '#rt-deleted'];
	for (let i=0 ; i<s.length ; ++i) {
		$(s[i]).find('.corp-'+rv.c).remove();
		if ($(s[i]).find('tr').length == 1) {
			$(s[i]).hide();
		}
	}

	if ($('#rt-added,#rt-deleted').find('tr').length <= 2) {
		$('.rt-added,.rt-deleted,.rt-add-del-warn').hide();
	}
}

function event_scroll() {
	$('.nav-link.active').each(function() {
		if (!$(this).attr('data-hilite') && $(this).isInViewport()) {
			$(this).click();
		}
	});
}

$(function() {
	$('.rt-added,.rt-deleted,.rt-add-del-warn,.rt-changes').hide();

	init();
	load(0);

	$('.btnAcceptAll').off().click(btn_accept_all);
	$('.btnAcceptAllUntil').hide().off().click(btn_accept_all_until);
	$('.btnAcceptUnchanged').off().click(btn_accept_unchanged);
	$('.btnToggleUnchanged').off().click(btn_toggle_unchanged);

	$('.btnCheckedGoldReplace').off().click(btn_checked_gold_replace);
	$('.btnCheckedGoldAdd').off().click(btn_checked_gold_add);
	$('.btnCheckedAcceptUntil').off().click(btn_checked_accept_until);
	$('.btnCheckedAccept').off().click(btn_checked_accept);
	$('.btnCheckedInvert').off().click(btn_checked_invert);

	$('#selectDiffModeAll').change(function() {
		$('.selectDiffMode').val(this.value).change();
	});

	$(window).on('resize scroll', event_scroll);
});
