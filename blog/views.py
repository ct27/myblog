import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from .forms import CommentForm, PostModelForm
from .models import Comment, PostModel

@login_required
def post_model_create_view(request):
    ImageFormSet = formset_factory(Images, form=ImageForm)

    if request.method == 'POST':
        form = PostModelForm(request.POST, request.FILES)
        formset = ImageFormSet(request.POST, request.FILES, queryset=Images.objects.none())

        if form.is_valid() and formset.is_valid():
            post_form = form.save(commit=False)
            post_form.author = request.user
            post_form.save()

            for f in formset.cleaned_data:
                image = f['image']
                photo = Images(post=post_form, image=image)
                photo.save()
            messages.success(request, _("Created a new post!"))
            return HttpResponseRedirect("/blog/{slug}".format(slug=post_form.slug))
        else:
            print(form.errors, formset.errors)
    else:
        form = PostModelForm()
        formset = ImageFormSet(queryset=Images.objects.none())
    template = "blog/create_post.html"
    # return render(request, template, context)
    return render(request, template, {'form': PostModelForm, 'formset': formset}, context_instance=RequestContext(request))

#@login_required
def post_model_update_view(request, id=None):
    obj = get_object_or_404(PostModel, id=id)
    form = PostModelForm(request.POST or None, instance=obj)
    context = {
        "form": form
    }
    if form.is_valid():
        obj = form.save(commit=False)
        obj.save()
        messages.success(request, _("Updated the post!"))
        return HttpResponseRedirect("/blog/{num}".format(num=obj.id))
    
    template = "blog/update.html"
    return render(request, template, context)


class BlogDetailSlugView(DetailView):

    template_name = "blog/details.html"
    queryset = PostModel.objects.all()

    def get_context_data(self, **kwargs):
        context = super(BlogDetailSlugView, self).get_context_data(**kwargs)
        return context

def post_model_delete_view(request, id=None):
    obj = get_object_or_404(PostModel, id=id)
    if request.method == "POST":
        obj.delete()
        messages.success(request, _("Deleted post!"))
        return HttpResponseRedirect("/")
    context = {
        "object": obj,
    }
    template = "blog/delete.html"
    return render(request, template, context)


def post_model_list_view(request):
    query = request.GET.get("q", None)
    qs = PostModel.objects.all().order_by('-publish_date')
    paginator = Paginator(qs, 6)
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)

    index = items.number - 1
    max_index = len(paginator.page_range)
    start_index = index - 5 if index >= 5 else 0
    end_index = index + 5 if index <= max_index - 5 else max_index
    page_range = paginator.page_range[start_index:end_index]

    if query is not None:
        qs = qs.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(slug__icontains=query)
                )
    context = {
        "object_list": qs,
        "items": items,
        "page_range": page_range,
    }
    template = "blog/index.html"
    return render(request, template, context)



@login_required(login_url='/login/')
def login_required_view(request):
    print(request.user)
    qs = PostModel.objects.all()
    context = {
        "object_list": qs,
    }

    if request.user.is_authenticated():
        template = "blog/index.html"
    else:
        template = "blog/list_view_public.html"
        #raise Http404
        return HttpResponseRedirect("/login")
    
    return render(request, template, context)




def post_model_robust_view(request, id=None):
    obj = None
    context =  {}
    success_message = _('Created a new post!')
    
    if id is None:
        "obj có thể được tạo ra"
        template = "blog/post.html"
    else:
        "obj prob exists"
        obj = get_object_or_404(PostModel, id=id)
        #success_message = _('Created a new post')
        context["object"] = obj
        template = "blog/details.html"
        if "edit" in request.get_full_path():
            template = "blog/update.html"
        if "delete" in request.get_full_path():
            template = "blog/delete.html"
            if request.method == "POST":
                obj.delete()
                messages.success(request, _("Deleted post!"))
                return HttpResponseRedirect("/blog/")

    #if "edit" in request.get_full_path() or "create" in request.get_full_path():
    form = PostModelForm(request.POST or None, instance=obj)
    context["form"] = form
    if form.is_valid():
        obj = form.save(commit=False)
        obj.save()
        messages.success(request, success_message)
        if obj is not None:
            return HttpResponseRedirect("/blog/{num}".format(obj.id))
        context["form"] - PostModelForm()
    return render(request, template, context)

def comments(request, id):
    post = get_object_or_404(PostModel, id=id)
    if request.method == 'POST':
        form = CommentForm(request.POST, author=request.user)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = form.author
            comment.save()
            return redirect('blog:detail', id=post.id)
    else:
        form = CommentForm()
        return render(request, 'blog/comments.html', {"form":form})

def Home(request):
    query = request.GET.get("q", None)
    qs = PostModel.objects.all().order_by('-publish_date')
    paginator = Paginator(qs, 6)
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)

    index = items.number - 1
    max_index = len(paginator.page_range)
    start_index = index - 5 if index >= 5 else 0
    end_index = index + 5 if index <= max_index - 5 else max_index
    page_range = paginator.page_range[start_index:end_index]

    if query is not None:
        qs = qs.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(slug__icontains=query)
                )
    context = {
        "object_list": qs,
        "items": items,
        "page_range": page_range,
    }
    template = "blog/index.html"
    return render(request, template, context)

def windows(request):
    query = request.GET.get("q", None)
    qs = PostModel.objects.all().order_by('-publish_date').filter(kind="windows")
    paginator = Paginator(qs, 6)
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)

    index = items.number - 1
    max_index = len(paginator.page_range)
    start_index = index - 5 if index >= 5 else 0
    end_index = index + 5 if index <= max_index - 5 else max_index
    page_range = paginator.page_range[start_index:end_index]

    if query is not None:
        qs = qs.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(slug__icontains=query)
                )
    context = {
        "object_list": qs,
        "items": items,
        "page_range": page_range,
    }
    template = "blog/windows.html"
    return render(request, template, context)

def linux(request):
    query = request.GET.get("q", None)
    qs = PostModel.objects.all().order_by('-publish_date').filter(kind="linux")
    paginator = Paginator(qs, 6)
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)

    index = items.number - 1
    max_index = len(paginator.page_range)
    start_index = index - 5 if index >= 5 else 0
    end_index = index + 5 if index <= max_index - 5 else max_index
    page_range = paginator.page_range[start_index:end_index]

    if query is not None:
        qs = qs.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(slug__icontains=query)
                )
    context = {
        "object_list": qs,
        "items": items,
        "page_range": page_range,
    }
    template = "blog/linux.html"
    return render(request, template, context)

def technology(request):
    query = request.GET.get("q", None)
    qs = PostModel.objects.all().order_by('-publish_date').filter(kind="technology")
    paginator = Paginator(qs, 6)
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)

    index = items.number - 1
    max_index = len(paginator.page_range)
    start_index = index - 5 if index >= 5 else 0
    end_index = index + 5 if index <= max_index - 5 else max_index
    page_range = paginator.page_range[start_index:end_index]

    if query is not None:
        qs = qs.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(slug__icontains=query)
                )
    context = {
        "object_list": qs,
        "items": items,
        "page_range": page_range,
    }
    template = "blog/technology.html"
    return render(request, template, context)

def entertain(request):
    query = request.GET.get("q", None)
    qs = PostModel.objects.all().order_by('-publish_date').filter(kind="entertain")
    paginator = Paginator(qs, 6)
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)

    index = items.number - 1
    max_index = len(paginator.page_range)
    start_index = index - 5 if index >= 5 else 0
    end_index = index + 5 if index <= max_index - 5 else max_index
    page_range = paginator.page_range[start_index:end_index]

    if query is not None:
        qs = qs.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(slug__icontains=query)
                )
    context = {
        "object_list": qs,
        "items": items,
        "page_range": page_range,
    }
    template = "blog/entertain.html"
    return render(request, template, context)

def test_view(request):
    template = "admin/accounts/accounts.html"
    context = {}
    return render(request, template, context)