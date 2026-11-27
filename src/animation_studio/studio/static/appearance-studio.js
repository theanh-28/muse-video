(() => {
  const prior = window.ScriptStudio;
  if (!prior) return;
  const token = document.querySelector('meta[name="studio-token"]')?.content;
  const api = async (path, method = 'GET', body) => {
    const response = await fetch(path, {method, headers: {'Content-Type': 'application/json', 'X-Studio-Token': token}, body: body && JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw Error(data.detail || `HTTP ${response.status}`);
    return data;
  };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const artifact = (run, id) => run.workflow?.artifacts?.[`appearance:${id}`]?.at(-1);
  const dirty = new Set();
  const renderAppearance = run => {
    const root = document.getElementById('run-view');
    const cards = (run.appearance_specs || []).map(spec => {
      const current = artifact(run, spec.character_id);
      const scopes = (run.asset_generation_approvals || []).filter(item => item.operation_type === 'IMAGE' && item.target_artifact_id === `appearance:${spec.character_id}` && item.target_revision === current?.revision && item.target_content_hash === current?.content_hash && item.request_fingerprint && item.approved_request);
      const scope = scopes.at(-1);
      const attempts = Object.fromEntries((run.asset_generation_attempts || []).map(item => [item.attempt_id, item]));
      const candidates = spec.candidates.map(candidate => { const attempt = attempts[candidate.attempt_id] || {}; const state = candidate.status === 'APPROVED' ? 'APPROVED' : (attempt.status || candidate.status); const err = attempt.error || candidate.error; return `<li>${candidate.image_path ? `<img width="120" src="/api/runs/${run.run_id}/appearance-image/${candidate.candidate_id}" alt="candidate">` : ''}${esc(candidate.candidate_id.slice(0, 8))} · ${esc(state)} ${err ? esc(err) : ''} ${state === 'SUBMISSION_UNKNOWN' ? '<em> reconciliation required</em>' : ''} ${state === 'SUBMISSION_INTENDED' ? `<button data-submit="${candidate.attempt_id}">Gửi</button>` : ''}${['SUBMITTED','RUNNING'].includes(state) ? `<button data-refresh="${candidate.attempt_id}">Làm mới</button>` : ''}${state === 'COMPLETED' && candidate.candidate_id !== spec.selected_candidate_id ? `<button data-select="${esc(spec.character_id)}:${esc(candidate.candidate_id)}">Chọn</button>` : ''}${candidate.candidate_id === spec.selected_candidate_id ? `✓ selected ${!spec.approved_candidate_id ? `<button data-final="${spec.character_id}:${candidate.content_hash}">Duyệt ảnh</button>` : ''}` : ''}</li>`; }).join('') || '<li>Chưa có candidate.</li>';
      return `<article class="shot-card"><h3>${esc(spec.character_name)} <span class="status-tag">${esc(spec.character_id)}</span></h3><label>Mô tả tạo hình<textarea data-description="${esc(spec.character_id)}">${esc(spec.description)}</textarea></label><p>Scope hiện tại: ${scope ? `${scope.reserved_requests}/${scope.request_limit} intent` : 'chưa duyệt'}${scopes.length > 1 ? ` (${scopes.length - 1} scope cũ)` : ''}</p><p>Candidate: ${spec.candidates.length}</p><div class="panel-actions"><button data-edit="${esc(spec.character_id)}">Lưu bản sửa</button>${current?.status === 'DRAFT' ? `<button data-spec="${esc(spec.character_id)}">Duyệt mô tả</button>` : ''}${current?.status === 'APPROVED' && (!scope || scope.reserved_requests >= scope.request_limit) ? `<button data-scope="${esc(spec.character_id)}">Duyệt ${scope ? 'scope mới' : '3 request'}</button>` : ''}${scope && scope.reserved_requests < scope.request_limit ? `<button data-prepare="${esc(spec.character_id)}:${esc(scope.approval_id)}">Chuẩn bị ${Math.min(3, scope.request_limit - scope.reserved_requests)} intent</button>` : ''}</div><ul>${candidates}</ul></article>`;
    }).join('');
    root.innerHTML = `<section class="script-studio"><h2>Tạo hình nhân vật</h2><p>Scope approval chỉ chuẩn bị các intent; Studio không gửi Muse khi chưa có quyền live riêng.</p><div class="shot-grid">${cards || '<p>Không có nhân vật chính cần tạo hình.</p>'}</div></section>`;
    root.querySelectorAll('[data-description]').forEach(field => field.oninput = () => dirty.add(`${run.run_id}:${field.dataset.description}`));
    root.querySelectorAll('[data-edit]').forEach(button => button.onclick = async () => { const character_id = button.dataset.edit, a = artifact(run, character_id), field = root.querySelector(`[data-description="${character_id}"]`); button.disabled = true; try { const saved = await api(`/api/runs/${run.run_id}/appearance/specification`, 'PUT', {character_id, expected_revision:a.revision, expected_content_hash:a.content_hash, description:field.value, locked_attributes: (run.appearance_specs.find(item => item.character_id === character_id)?.locked_attributes || [])}); dirty.delete(`${run.run_id}:${character_id}`); renderAppearance(saved); } catch (e) { alert(e.message); button.disabled = false; } });
    root.querySelectorAll('[data-spec]').forEach(button => button.onclick = async () => { const a = artifact(run, button.dataset.spec); await api(`/api/runs/${run.run_id}/appearance/specification/approve`, 'POST', {character_id: button.dataset.spec, expected_revision:a.revision, expected_content_hash:a.content_hash, approved_by:'Studio user'}).then(renderAppearance).catch(e=>alert(e.message)); });
    root.querySelectorAll('[data-scope]').forEach(button => button.onclick = async () => { const a = artifact(run, button.dataset.scope); await api(`/api/runs/${run.run_id}/appearance/generation/approve`, 'POST', {character_id: button.dataset.scope, expected_revision:a.revision, expected_content_hash:a.content_hash, request_limit:3, approved_by:'Studio user'}).then(renderAppearance).catch(e=>alert(e.message)); });
    root.querySelectorAll('[data-prepare]').forEach(button => button.onclick = async () => { const [character_id, approval_id] = button.dataset.prepare.split(':'); await api(`/api/runs/${run.run_id}/appearance/candidates/prepare`, 'POST', {character_id, approval_id, count:3}).then(renderAppearance).catch(e=>alert(e.message)); });
    root.querySelectorAll('[data-select]').forEach(button => button.onclick = async () => { const [character_id, candidate_id] = button.dataset.select.split(':'); await api(`/api/runs/${run.run_id}/appearance/candidate/select`, 'POST', {character_id, candidate_id}).then(renderAppearance).catch(e=>alert(e.message)); });
    root.querySelectorAll('[data-submit]').forEach(button => button.onclick = async () => { button.disabled=true; await api(`/api/runs/${run.run_id}/appearance/submit`, 'POST', {attempt_id:button.dataset.submit}).then(renderAppearance).catch(e=>{alert(e.message);button.disabled=false;}); });
    root.querySelectorAll('[data-refresh]').forEach(button => button.onclick = async () => { button.disabled=true; await api(`/api/runs/${run.run_id}/appearance/refresh`, 'POST', {attempt_id:button.dataset.refresh}).then(renderAppearance).catch(e=>{alert(e.message);button.disabled=false;}); });
    root.querySelectorAll('[data-final]').forEach(button => button.onclick = async () => { const [character_id, expected_content_hash] = button.dataset.final.split(':'); await api(`/api/runs/${run.run_id}/appearance/reference/approve`, 'POST', {character_id, expected_content_hash, approved_by:'Studio user'}).then(renderAppearance).catch(e=>alert(e.message)); });
  };
  window.ScriptStudio = {
    ...prior,
    handles: run => prior.handles(run) || run.status === 'ASSET_PREPARATION',
    render: run => {
      if (run.status === 'ASSET_PREPARATION') return renderAppearance(run);
      prior.render(run);
      if (run.status === 'SCRIPT_APPROVED') {
        const actions = document.querySelector('.script-actions');
        if (actions && !document.getElementById('appearance-start')) {
          const button = document.createElement('button'); button.id='appearance-start'; button.textContent='Chuẩn bị tạo hình nhân vật';
          button.onclick = async () => { button.disabled=true; try { renderAppearance(await api(`/api/runs/${run.run_id}/appearance/prepare`, 'POST', {})); } catch (error) { alert(error.message); button.disabled=false; } };
          actions.append(button);
        }
      }
    },
  };
})();
