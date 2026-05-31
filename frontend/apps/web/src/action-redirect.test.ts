// Lock the action-redirect routing (#620). `navigate` for SPA-internal
// paths, `window.location.assign` (injected as `assignLocation` for
// testability) for everything else. The legacy behaviour piped every
// redirect through `navigate` — which silently no-op'd for any URL
// outside the SPA mount.
import { describe, expect, it, vi } from 'vitest';

import { followActionRedirect } from './action-redirect';

const MOUNT = '/admin-react/';
const ORIGIN = 'http://localhost:3000';

function makeArgs(redirect: string) {
  const navigate = vi.fn();
  const assignLocation = vi.fn();
  return {
    args: { redirect, mount: MOUNT, navigate, currentOrigin: ORIGIN, assignLocation },
    navigate,
    assignLocation,
  };
}

describe('followActionRedirect', () => {
  it('uses navigate for a same-origin path inside the SPA mount', () => {
    const { args, navigate, assignLocation } = makeArgs('/admin-react/auth/user/42/');
    followActionRedirect(args);
    // The mount prefix is stripped so BrowserRouter's basename
    // doesn't double up. Trailing slash before the relative path is
    // preserved.
    expect(navigate).toHaveBeenCalledWith('/auth/user/42/');
    expect(assignLocation).not.toHaveBeenCalled();
  });

  it('preserves search + hash when navigating client-side', () => {
    const { args, navigate } = makeArgs('/admin-react/auth/user/42/?tab=audit#log');
    followActionRedirect(args);
    expect(navigate).toHaveBeenCalledWith('/auth/user/42/?tab=audit#log');
  });

  it('falls back to assignLocation for a same-origin path OUTSIDE the mount', () => {
    // Legacy admin path — must be a full browser navigation since
    // React Router only routes within the SPA mount.
    const { args, navigate, assignLocation } = makeArgs('/admin/auth/user/42/change/');
    followActionRedirect(args);
    expect(assignLocation).toHaveBeenCalledWith('/admin/auth/user/42/change/');
    expect(navigate).not.toHaveBeenCalled();
  });

  it('falls back to assignLocation for cross-origin URLs', () => {
    // The signed-S3-download case — must be a real browser navigation
    // so the download starts on the operator's machine.
    const { args, navigate, assignLocation } = makeArgs('https://s3.example.com/signed/file.pdf');
    followActionRedirect(args);
    expect(assignLocation).toHaveBeenCalledWith('https://s3.example.com/signed/file.pdf');
    expect(navigate).not.toHaveBeenCalled();
  });

  it('falls back to assignLocation for a hijack-style /hijack/... URL', () => {
    // Common third-party pattern (`django-hijack`) — action returns
    // `HttpResponseRedirect("/hijack/release-user/?next=...")`.
    const { args, navigate, assignLocation } = makeArgs('/hijack/release-user/?next=/admin/foo/');
    followActionRedirect(args);
    expect(assignLocation).toHaveBeenCalledWith('/hijack/release-user/?next=/admin/foo/');
    expect(navigate).not.toHaveBeenCalled();
  });

  it('falls back to assignLocation on an unparseable URL', () => {
    // A malformed input shouldn't make the operator's click disappear
    // into the void — surface it as a real navigation and let the
    // browser report the failure to the user.
    //
    // Using "http://" alone — bare scheme with no authority — produces
    // a TypeError in the URL constructor on all majors.
    const { args, navigate, assignLocation } = makeArgs('http://');
    followActionRedirect(args);
    expect(assignLocation).toHaveBeenCalledWith('http://');
    expect(navigate).not.toHaveBeenCalled();
  });
});
