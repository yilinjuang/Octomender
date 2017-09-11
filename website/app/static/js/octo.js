/* Helper functions. */
let getAjax = (url, success) => {
    let xhr = new XMLHttpRequest();
    xhr.open('GET', url);
    xhr.onload = () => {
        if (xhr.status === 200) {
            try {
                let json = JSON.parse(xhr.responseText);
                success(json);
            } catch (err) {
                console.log(`getAjax response parsing failed: ${xhr.responseText}`);
            }
        } else {
            console.log(`getAjax status failed: ${url}, ${xhr.status}`);
        }
    };
    xhr.send();
};

let renderRepoList = (type, repos) => {
    let html = '';
    for (let repo of repos) {
        if (type === 'suggest') {
            html +=
`<li class="${type}-vote mdl-list__item mdl-list__item--two-line" data-id="${repo.id}">
    <button class="mdl-button mdl-js-button mdl-button--icon mdl-button--primary">
        <i class="material-icons">sentiment_very_satisfied</i>
    </button>
    <button class="mdl-button mdl-js-button mdl-button--icon mdl-button--accent">
        <i class="material-icons">sentiment_neutral</i>
    </button>
</li>
`;
        }
        html +=
`<li class="${type}-item mdl-list__item mdl-list__item--two-line" data-url="${repo.url}">
    <span class="mdl-list__item-primary-content">
        <div class="octicon-repo mdl-list__item-avatar"></div>
        <span>${repo.name}</span>
        <span class="mdl-list__item-sub-title">${repo.desc}</span>
    </span>
    <span class="mdl-list__item-secondary-content">
        <div class="octicon-star mdl-list__item-icon"></div>
        <span class="star-number mdl-list__item-secondary-info">${repo.num_stars}</span>
    </span>
</li>
`;
    }
    return html;
};

// Limit item description length.
let truncateItem = item => {
    let desc = item.querySelector('.mdl-list__item-sub-title');
    // Cut half.
    while (desc.offsetHeight > 45) {
        desc.innerText = desc.innerText.slice(
            0, Math.floor(desc.innerText.length/2)) + '...';
    }
    // Cut 5 letters.
    while (desc.offsetHeight > 18) {
        desc.innerText = desc.innerText.slice(0, -8) + '...';
    }

    let title = desc.previousElementSibling;
    let icon = document.querySelector('.octicon-repo');  // Used to indicate if on mobile device.
    if (window.getComputedStyle(icon).display === 'none') {
        title.innerText = title.innerText.split('/')[1];
    }
};

/* Main functions */
// Cards.
let actionCard = document.querySelector('.action-card');
let suggestCard = document.querySelector('.suggest-card');
let starCard = document.querySelector('.star-card');

// Action card.
if (actionCard !== null) {
    let suggestButton = actionCard.querySelector('.mdl-button');
    let progressBar = actionCard.querySelector('.mdl-progress');
    let syncing;
    let updateProgress = function() {
        getAjax('progress', res => {
            // console.log(`updateProgress: ${res.progress}`);
            let now = progressBar.MaterialProgress.progressbar_.style.width;
            if (parseFloat(now) < res.progress) {
                progressBar.MaterialProgress.setProgress(res.progress);
            }
            if (res.progress === 100.0) {
                progressBar.className += ' mdl-progress__indeterminate';
                clearInterval(syncing);
            }
        });
    };
    suggestButton.addEventListener('click', () => {
        actionCard.querySelector('.mdl-card__actions').style.display = 'none';
        progressBar.style.display = 'block';
        let actionTitle = actionCard.querySelector('.mdl-card__title');
        let actionTitleText = actionCard.querySelector('.mdl-card__title-text');
        actionTitleText.innerText = `Suggesting...`;
        syncing = setInterval(updateProgress, 1000);
        getAjax('suggest', res => {
            // console.log(res);
            clearInterval(syncing);
            if (res.error_msg !== null) {
                actionTitleText.innerText = res.error_msg;
                actionTitle.style.margin = 'auto 0';
                progressBar.style.display = 'none';
            } else {
                progressBar.MaterialProgress.setProgress(100.0);
                actionCard.style.display = 'none';
                suggestCard.style.display = 'flex';
                renderSuggestCard(res.suggest_repos, res.vote);
                hintDialog.showModal();
            }
        });
    });
}

// Suggest card.
let renderSuggestCard = (repos, votes) => {
    let html = renderRepoList('suggest', repos);
    suggestCard.querySelector('.mdl-list').innerHTML = html;
    suggestCard.querySelector('.mdl-spinner').style.display = 'none';

    for (let suggestVote of suggestCard.querySelectorAll('.suggest-vote')) {
        let id = suggestVote.dataset.id;
        for (let voteButton of suggestVote.querySelectorAll('.mdl-button')) {
            componentHandler.upgradeElement(voteButton); // Register new button.
            let updown = voteButton.className.includes('mdl-button--primary') ? 1 : -1;
            if (updown === votes[id]) {
                voteButton.disabled = true;
            }
            voteButton.addEventListener('click', () => {
                voteButton.disabled = true;
                if (updown === 1) {
                    voteButton.parentElement.nextElementSibling.style.backgroundColor = '#dadfff';
                    voteButton.nextElementSibling.disabled = false;
                } else {
                    voteButton.parentElement.nextElementSibling.style.backgroundColor = '#ffe0eb';
                    voteButton.previousElementSibling.disabled = false;
                }
                getAjax(`vote/${updown}/${id}`, res => {
                    // console.log(res);
                });
            });
        }
        if (votes[id] === 1) {
            suggestVote.nextElementSibling.style.backgroundColor = '#dadfff';
        } else if (votes[id] === -1) {
            suggestVote.nextElementSibling.style.backgroundColor = '#ffe0eb';
        }
    }
    for (let suggestItem of suggestCard.querySelectorAll('.suggest-item')) {
        truncateItem(suggestItem);

        suggestItem.addEventListener('click', e => {
            let url = e.currentTarget.dataset.url;
            window.open(url, '_blank');
        });
    }
};
if (suggestCard.style.display !== 'none') {
    getAjax('suggest', res => {
        renderSuggestCard(res.suggest_repos, res.vote);
    });
}

// Star card. (maybe action card also)
if (starCard !== null) {
    getAjax('star', res => {
        // No stars found.
        if (Object.keys(res).length === 0 && res.constructor === Object) {
            actionCard.querySelector('.mdl-card__title-text').innerText =
                `Sorry, octomender can't find any stars of you...`;
            actionCard.querySelector('.mdl-card__title').style.display = 'flex';
            actionCard.querySelector('.mdl-card__title').style.margin = 'auto 0';
            actionCard.querySelector('.mdl-spinner').style.display = 'none';
            starCard.style.display = 'none';
            return;
        }

        if (actionCard !== null) {
            actionCard.querySelector('.mdl-card__title-text').innerText =
                `You have starred ${res.num_repos} repos since ${res.since_year}.`;
            actionCard.querySelector('.mdl-card__title').style.display = 'flex';
            actionCard.querySelector('.mdl-card__actions').style.display = 'block';
            actionCard.querySelector('.mdl-spinner').style.display = 'none';
        }

        let html = renderRepoList('star', res.repos);
        starCard.querySelector('.mdl-list').innerHTML = html;
        starCard.querySelector('.mdl-spinner').style.display = 'none';

        for (let starItem of starCard.querySelectorAll('.star-item')) {
            truncateItem(starItem);

            starItem.addEventListener('click', e => {
                let url = e.currentTarget.dataset.url;
                window.open(url, '_blank');
            });
        }
    });
}

// Hint dialog.
let hintDialog = document.querySelector('dialog');
if (hintDialog !== null) {
    if (!hintDialog.showModal) {
        dialogPolyfill.registerDialog(hintDialog);
    }
    hintDialog.querySelector('.close').addEventListener('click', function() {
        hintDialog.close();
    });
}
