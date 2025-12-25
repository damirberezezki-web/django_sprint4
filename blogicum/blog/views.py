from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CommentForm, PostForm, RegistrationForm, UserForm
from .models import Category, Comment, Post

POSTS_PER_PAGE = 10

User = get_user_model()


def get_published_posts():
    return (
        Post.objects.select_related('category', 'location', 'author')
        .filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        )
        .annotate(comment_count=Count('comments'))
        .order_by('-pub_date')
    )


def paginate_posts(request, queryset):
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def get_post_for_user(post_id, user):
    base_qs = Post.objects.select_related('category', 'location', 'author')
    if user.is_authenticated:
        own_post = base_qs.filter(pk=post_id, author=user).first()
        if own_post:
            return own_post
    return get_object_or_404(
        base_qs.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        ),
        pk=post_id,
    )


def index(request):
    page_obj = paginate_posts(request, get_published_posts())
    return render(request, 'blog/index.html', {'page_obj': page_obj})


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True,
    )
    page_obj = paginate_posts(
        request,
        get_published_posts().filter(category=category),
    )
    return render(
        request,
        'blog/category.html',
        {'category': category, 'page_obj': page_obj},
    )


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    if request.user == profile_user:
        posts = (
            Post.objects.select_related('category', 'location', 'author')
            .filter(author=profile_user)
            .annotate(comment_count=Count('comments'))
            .order_by('-pub_date')
        )
    else:
        posts = get_published_posts().filter(author=profile_user)
    page_obj = paginate_posts(request, posts)
    return render(
        request,
        'blog/profile.html',
        {'profile': profile_user, 'page_obj': page_obj},
    )


def post_detail(request, post_id):
    post = get_post_for_user(post_id, request.user)
    comments = (
        Comment.objects.select_related('author')
        .filter(post=post)
        .order_by('created_at')
    )
    context = {'post': post, 'comments': comments}
    if request.user.is_authenticated:
        context['form'] = CommentForm()
    return render(request, 'blog/detail.html', context)


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = PostForm()
    return render(request, 'blog/create.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form, 'post': post})


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author and not request.user.is_staff:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:index')
    form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form, 'post': post})


@login_required
def add_comment(request, post_id):
    post = get_post_for_user(post_id, request.user)
    form = CommentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('blog:post_detail', post_id=post_id)
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    post = get_post_for_user(post_id, request.user)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        form = CommentForm(instance=comment)
    return render(
        request,
        'blog/comment.html',
        {'form': form, 'comment': comment},
    )


@login_required
def delete_comment(request, post_id, comment_id):
    post = get_post_for_user(post_id, request.user)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if request.user != comment.author and not request.user.is_staff:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {'comment': comment})


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = UserForm(instance=request.user)
    return render(request, 'blog/user.html', {'form': form})


def registration(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'registration/registration_form.html', {'form': form})
