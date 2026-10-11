#!/bin/bash

update () {
    if [ -d "$BASE/$2/.git" ]; then
        pushd "$BASE/$2"
        git reset --hard
        git checkout $BRANCH
        git pull
        popd
    else
        if [ -e "$REFS/$2/.git" ]; then
            if [ $REFS = $BASE ]; then
                git reset --hard
                git pull
            else
                git clone $1 "$BASE/$2" --reference "$REFS/$2"
            fi

            pushd "$BASE/$2"
            git checkout $BRANCH
            popd

        else
            git clone $1 "$BASE/$2"
            pushd "$BASE/$2"
            git checkout $BRANCH
            popd
        fi
    fi
}

if [ "$NOPULL" != 1 ]; then
    update $(git remote get-url origin)
    python3 "$ROOT/tools/prepare_engine.py" "$BASE/renpy" \
        --repository "${RENPY_ENGINE_REPOSITORY:-https://github.com/potato-flower-alt/renpy.git}" \
        --branch "${RENPY_ENGINE_BRANCH:-$BRANCH}"
fi

rm -Rf "$BASE/renpy/tmp/gen3"
rm -Rf "$BASE/renpy/tmp/gen3-static"
